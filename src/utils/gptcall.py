"""
GPT API Interaction Module

This module provides functions for interacting with OpenAI's GPT models,
processing responses, and managing a local cache of previous interactions.
"""

import json
import os
import uuid
from typing import Dict, List, Optional, Union, Literal
from hashlib import md5
import logging
from datetime import datetime
from pathlib import Path

import openai
from pydantic import BaseModel, Field, field_validator


class ChatMessage(BaseModel):
    """Representation of a message in a chat conversation."""

    role: Literal["system", "user", "assistant"] = Field(
        ..., description="The role of the message sender (system, user, or assistant)"
    )
    content: str = Field(..., description="The content of the message")


class ChatCompletionRequest(BaseModel):
    """Input parameters for a GPT chat completion request."""

    prompt: str = Field(..., description="The user's prompt to send to the model")
    system: str = Field(
        "", description="Optional system message to set context or behavior"
    )
    model: str = Field(
        "gpt-4-turbo", description="The GPT model to use for the completion"
    )
    temperature: float = Field(
        0.2,
        description="Controls randomness (0-1, lower is more deterministic)",
        ge=0.0,
        le=1.0,
    )
    top_p: float = Field(
        0.9, description="Controls diversity via nucleus sampling (0-1)", ge=0.0, le=1.0
    )
    max_tokens: int = Field(
        -1, description="Maximum number of tokens to generate, -1 means no limit"
    )

    @field_validator("temperature")
    def validate_temperature(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Temperature must be between 0 and 1")
        return v

    @field_validator("top_p")
    def validate_top_p(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Top_p must be between 0 and 1")
        return v


class StoredResponse(BaseModel):
    """Structure for storing and retrieving GPT responses."""

    prompt: str = Field(..., description="The original prompt sent to the model")
    response: str = Field(..., description="The response received from the model")
    prompt_hash: str = Field(
        ..., description="MD5 hash of the prompt for quick lookups"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="When this response was generated",
    )
    model: str = Field("unknown", description="The model that generated this response")


def post_processing(response: str) -> str:
    """
    Parse and extract Groovy code snippets from the model's response.

    Args:
        response: The raw response text from the GPT model

    Returns:
        The extracted Groovy code if available, otherwise the original response

    Examples:
        >>> post_processing("Here is some code: ```groovy\\nprint('Hello')\\n```")
        "print('Hello')"
    """
    # Extract the code between ```groovy and ```
    if "```groovy" not in response:
        return response
    return response.split("```groovy")[1].split("```")[0]


def get_storage_path() -> Path:
    """
    Get the path to the GPT response storage directory.

    Returns:
        Path object pointing to the storage directory

    Note:
        Creates the directory if it doesn't exist
    """
    storage_dir = Path("gpt_response")
    storage_dir.mkdir(exist_ok=True)
    return storage_dir


def store_response(prompt: str, response: str, model: str = "unknown") -> Path:
    """
    Store a prompt and its response to a JSON file for future retrieval.

    Args:
        prompt: The user's original prompt
        response: The model's response to be stored
        model: The model name that generated the response

    Returns:
        Path to the stored response file

    Examples:
        >>> file_path = store_response("Hello", "Hi there!", "gpt-4-turbo")
        >>> print(f"Response stored in {file_path}")
    """
    uuid_str = str(uuid.uuid4())
    storage_dir = get_storage_path()

    stored_data = StoredResponse(
        prompt=prompt,
        response=response,
        prompt_hash=md5(prompt.encode()).hexdigest(),
        model=model,
    )

    file_path = storage_dir / f"api_response_{uuid_str}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(stored_data.model_dump_json(indent=2))

    return file_path


def find_previous_response(prompt: str) -> Optional[str]:
    """
    Find a previously stored response for a given prompt.

    Args:
        prompt: The prompt to search for

    Returns:
        The previously stored response if found, None otherwise

    Examples:
        >>> response = find_previous_response("What is Python?")
        >>> if response:
        ...     print("Found cached response")
    """
    prompt_hash = md5(prompt.encode()).hexdigest()
    storage_dir = get_storage_path()

    if not storage_dir.exists():
        return None

    for file_path in storage_dir.glob("api_response_*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("prompt_hash") == prompt_hash:
                    return data["response"]
        except (json.JSONDecodeError, KeyError) as e:
            logging.warning(f"Error reading cached response file {file_path}: {e}")

    return None


def GPTChatCompletion(
    prompt: str,
    system: str = "",
    model: str = "gpt-4-mini",
    temperature: float = 0.2,
    top_p: float = 0.9,
    max_tokens: int = -1,
) -> Optional[str]:
    """
    Send a prompt to OpenAI's GPT models and get a completion response.

    This function first checks if a cached response exists. If not, it calls
    the OpenAI API and stores the response for future use.

    Args:
        prompt: The user's prompt to send to the model
        system: Optional system message to set context or behavior
        model: The GPT model to use for the completion
        temperature: Controls randomness (0-1, lower is more deterministic)
        top_p: Controls diversity via nucleus sampling (0-1)
        max_tokens: Maximum tokens to generate, -1 for no limit

    Returns:
        The model's response text, or None if the request failed

    Examples:
        >>> response = GPTChatCompletion(
        ...     prompt="Explain quantum computing in simple terms",
        ...     system="You are a helpful assistant that explains complex topics simply."
        ... )
        >>> print(response)
    """
    # Validate input using Pydantic
    request = ChatCompletionRequest(
        prompt=prompt,
        system=system,
        model=model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )

    # Check cache for previous identical prompt
    previous_response = find_previous_response(request.prompt)
    if previous_response:
        logging.info(f"Using cached response for prompt: {prompt[:50]}...")
        return previous_response

    # Prepare messages for the API call
    if request.system:
        messages = [
            {"role": "system", "content": request.system},
            {"role": "user", "content": request.prompt},
        ]
    else:
        messages = [{"role": "user", "content": request.prompt}]

    try:
        # Make the API call with appropriate parameters
        if request.max_tokens == -1:
            response = openai.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                top_p=request.top_p,
            )
        else:
            response = openai.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                top_p=request.top_p,
                max_tokens=request.max_tokens,
            )

        # Extract and store the response
        response_text = response.choices[0].message.content
        store_response(request.prompt, response_text, request.model)
        return response_text
    except Exception as e:
        logging.error(f"Error during OpenAI API call: {e}")
        return None


def main():
    """
    Demonstrate the functionality of the GPTCall module.

    This function shows practical examples of each capability in the module,
    including making API calls, caching, and post-processing responses.
    """
    # Set up OpenAI API key (normally this would be in environment variables)
    # openai.api_key = "your-api-key-here"  # Uncomment and set your API key

    print("=" * 50)
    print("GPTCall Module Demonstration")
    print("=" * 50)

    # Example 1: Simple GPT completion
    print("\n1. Simple GPT Completion (simulated)")

    # Simulating a response for demonstration purposes
    mock_prompt = "What is Python programming language?"
    mock_response = """
    Python is a high-level, interpreted programming language known for its readability and simplicity.
    
    Here's a simple example:
    
    ```groovy
    def greet(name):
        return f"Hello, {name}!"
    
    print(greet("World"))
    ```
    
    Python is widely used in data science, web development, and automation.
    """

    # Store the mock response
    store_response(mock_prompt, mock_response, "mock-gpt-4")
    print(f"Stored a mock response for: '{mock_prompt}'")

    # Example 2: Finding a cached response
    print("\n2. Finding Cached Response")
    cached_response = find_previous_response(mock_prompt)
    if cached_response:
        print(f"Found cached response: '{cached_response[:50]}...'")
    else:
        print("No cached response found.")

    # Example 3: Post-processing to extract code
    print("\n3. Post-processing to Extract Code")
    extracted_code = post_processing(mock_response)
    print(f"Extracted Groovy code:\n{extracted_code}")

    # Example 4: Making a real API call (commented out to avoid actual API usage)
    print("\n4. Making a Real API Call (code disabled)")
    """
    # Uncomment to make an actual API call:
    system_prompt = "You are a helpful programming assistant."
    user_prompt = "Write a Python function to calculate the Fibonacci sequence."
    
    print(f"Sending prompt: '{user_prompt}'")
    response = GPTChatCompletion(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.7
    )
    
    if response:
        print(f"Received response: '{response[:100]}...'")
    else:
        print("Failed to get a response.")
    """

    # Example 5: Demonstrate request validation
    print("\n5. Request Validation")
    try:
        invalid_request = ChatCompletionRequest(
            prompt="Test prompt", temperature=2.0  # Invalid temperature (>1.0)
        )
        print("This should not be printed due to validation error")
    except Exception as e:
        print(f"Validation correctly caught error: {e}")

    print("\n" + "=" * 50)
    print("Demonstration complete!")


if __name__ == "__main__":
    main()
