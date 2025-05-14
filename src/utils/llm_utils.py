# /src/utils/gptcall.py

"""
LLM API Interaction Module

This module provides functions for interacting with various LLM providers (OpenAI, Google, Anthropic),
processing responses, and managing a local cache of previous interactions.
"""

import json
import uuid
import os
from typing import Optional, Literal, Dict, Any, List, Union
from hashlib import md5
import logging
from datetime import datetime
from pathlib import Path
import abc

import openai
from pydantic import BaseModel, Field, field_validator

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ChatMessage(BaseModel):
    """Representation of a message in a chat conversation."""

    role: Literal["system", "user", "assistant"] = Field(
        ..., description="The role of the message sender (system, user, or assistant)"
    )
    content: str = Field(..., description="The content of the message")


class ChatCompletionRequest(BaseModel):
    """Input parameters for a LLM chat completion request."""

    prompt: str = Field(..., description="The user's prompt to send to the model")
    system: str = Field(
        "", description="Optional system message to set context or behavior"
    )
    model: str = Field(
        "gpt-4-turbo", description="The LLM model to use for the completion"
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
    provider: str = Field(
        "", description="LLM provider to use (openai, gemini, claude, etc.)"
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
    """Structure for storing and retrieving LLM responses."""

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
    provider: str = Field(
        "unknown", description="The provider that generated this response"
    )


class LLMProvider(abc.ABC):
    """Abstract base class for LLM providers."""

    @abc.abstractmethod
    def complete(self, request: ChatCompletionRequest) -> Optional[str]:
        """
        Generate a completion for the given request.

        Args:
            request: The validated chat completion request

        Returns:
            The generated response text, or None if the request failed
        """
        pass

    @abc.abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.

        Returns:
            The provider name as a string
        """
        pass


class OpenAIProvider(LLMProvider):
    """Provider implementation for OpenAI models."""

    def __init__(self):
        # Check for API key in environment
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not found in environment variables")

    def get_provider_name(self) -> str:
        return "openai"

    def complete(self, request: ChatCompletionRequest) -> Optional[str]:
        """Generate a completion using OpenAI's API."""
        # Prepare messages for the API call
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})

        messages.append({"role": "user", "content": request.prompt})

        try:
            # Prepare API call parameters
            params = {
                "model": request.model,
                "messages": messages,
                "temperature": request.temperature,
                "top_p": request.top_p,
            }

            # Add max_tokens if specified
            if request.max_tokens != -1:
                params["max_tokens"] = request.max_tokens

            # Make the API call
            response = openai.chat.completions.create(**params)

            # Extract and return the response text
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error during OpenAI API call: {e}")
            return None


class GeminiProvider(LLMProvider):
    """Provider implementation for Google's Gemini models."""

    def __init__(self):
        # Import here to avoid requiring the package if not used
        try:
            import google.generativeai as genai

            self.genai = genai

            # Configure the API
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                self.genai.configure(api_key=api_key)
            else:
                logger.warning("GOOGLE_API_KEY not found in environment variables")
        except ImportError:
            logger.error(
                "google-generativeai package not installed. Run 'pip install google-generativeai'"
            )
            self.genai = None

    def get_provider_name(self) -> str:
        return "gemini"

    def complete(self, request: ChatCompletionRequest) -> Optional[str]:
        """Generate a completion using Gemini's API."""
        if not self.genai:
            logger.error("Gemini provider not properly initialized")
            return None

        try:
            # Map the model name (allow OpenAI model names to be mapped to Gemini)
            model_name = request.model
            if model_name.startswith("gpt-"):
                # Default mapping from OpenAI model names
                model_name = "gemini-pro"

            # Create a GenerativeModel instance
            model = self.genai.GenerativeModel(model_name=model_name)

            # Prepare the chat session
            chat = model.start_chat(history=[])

            # Add system prompt if provided
            if request.system:
                chat.send_message(request.system)

            # Send the user prompt and get response
            response = chat.send_message(
                request.prompt,
                generation_config={
                    "temperature": request.temperature,
                    "top_p": request.top_p,
                    "max_output_tokens": (
                        request.max_tokens if request.max_tokens > 0 else None
                    ),
                },
            )

            # Return the text response
            return response.text
        except Exception as e:
            logger.error(f"Error during Gemini API call: {e}")
            return None


class ClaudeProvider(LLMProvider):
    """Provider implementation for Anthropic's Claude models."""

    def __init__(self):
        # Import here to avoid requiring the package if not used
        try:
            import anthropic

            self.anthropic = anthropic

            # Configure the API
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.warning("ANTHROPIC_API_KEY not found in environment variables")

            self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        except ImportError:
            logger.error("anthropic package not installed. Run 'pip install anthropic'")
            self.anthropic = None
            self.client = None

    def get_provider_name(self) -> str:
        return "claude"

    def complete(self, request: ChatCompletionRequest) -> Optional[str]:
        """Generate a completion using Claude's API."""
        if not self.client:
            logger.error("Claude provider not properly initialized")
            return None

        try:
            # Map the model name (allow OpenAI model names to be mapped to Claude)
            model_name = request.model
            if model_name.startswith("gpt-"):
                # Default mapping from OpenAI model names
                model_name = "claude-3-opus-20240229"

            # Prepare the messages
            messages = []
            if request.system:
                messages.append({"role": "system", "content": request.system})

            messages.append({"role": "user", "content": request.prompt})

            # Send the API request
            response = self.client.messages.create(
                model=model_name,
                messages=messages,
                temperature=request.temperature,
                top_p=request.top_p,
                max_tokens=request.max_tokens if request.max_tokens > 0 else None,
            )

            # Return the text response
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error during Claude API call: {e}")
            return None


class LLMClient:
    """Factory class for managing LLM providers and generating completions."""

    _providers: Dict[str, LLMProvider] = {}
    _default_provider: str = ""

    @classmethod
    def initialize(cls) -> None:
        """Initialize the available providers."""
        # Register built-in providers
        cls.register_provider(OpenAIProvider())
        cls.register_provider(GeminiProvider())
        cls.register_provider(ClaudeProvider())

        # Set default provider from environment or fall back to OpenAI
        cls._default_provider = os.getenv("DEFAULT_LLM_PROVIDER", "openai").lower()

    @classmethod
    def register_provider(cls, provider: LLMProvider) -> None:
        """
        Register a new LLM provider.

        Args:
            provider: The LLM provider implementation to register
        """
        cls._providers[provider.get_provider_name()] = provider

    @classmethod
    def get_provider(cls, provider_name: str = "") -> Optional[LLMProvider]:
        """
        Get the specified provider by name.

        Args:
            provider_name: The name of the provider to get

        Returns:
            The provider instance, or None if not found
        """
        # Initialize providers if not done yet
        if not cls._providers:
            cls.initialize()

        # Use specified provider or default
        provider_name = (
            provider_name.lower() if provider_name else cls._default_provider
        )

        return cls._providers.get(provider_name)

    @classmethod
    def complete(cls, request: ChatCompletionRequest) -> Optional[str]:
        """
        Generate a completion using the appropriate provider.

        Args:
            request: The validated chat completion request

        Returns:
            The generated response text, or None if the request failed
        """
        # Get the specified provider or default
        provider = cls.get_provider(request.provider)

        if not provider:
            logger.error(
                f"Provider '{request.provider or cls._default_provider}' not available"
            )
            return None

        return provider.complete(request)


def post_processing(response: str) -> str:
    """
    Parse and extract Groovy code snippets from the model's response.

    Args:
        response: The raw response text from the LLM model

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
    Get the path to the LLM response storage directory.

    Returns:
        Path object pointing to the storage directory

    Note:
        Creates the directory if it doesn't exist
    """
    storage_dir = Path("gpt_response")
    storage_dir.mkdir(exist_ok=True)
    return storage_dir


def store_response(
    prompt: str, response: str, model: str = "unknown", provider: str = "unknown"
) -> Path:
    """
    Store a prompt and its response to a JSON file for future retrieval.

    Args:
        prompt: The user's original prompt
        response: The model's response to be stored
        model: The model name that generated the response
        provider: The provider that generated the response

    Returns:
        Path to the stored response file

    Examples:
        >>> file_path = store_response("Hello", "Hi there!", "gpt-4-turbo", "openai")
        >>> print(f"Response stored in {file_path}")
    """
    uuid_str = str(uuid.uuid4())
    storage_dir = get_storage_path()

    stored_data = StoredResponse(
        prompt=prompt,
        response=response,
        prompt_hash=md5(prompt.encode()).hexdigest(),
        model=model,
        provider=provider,
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


def llm_chat_completion(
    prompt: str,
    system: str = "",
    model: str = "gpt-4-mini",
    temperature: float = 0.2,
    top_p: float = 0.9,
    max_tokens: int = -1,
    provider: str = "",
) -> Optional[str]:
    """
    Send a prompt to an LLM model and get a completion response.

    This function first checks if a cached response exists. If not, it calls
    the appropriate LLM API and stores the response for future use.

    Args:
        prompt: The user's prompt to send to the model
        system: Optional system message to set context or behavior
        model: The model to use for the completion
        temperature: Controls randomness (0-1, lower is more deterministic)
        top_p: Controls diversity via nucleus sampling (0-1)
        max_tokens: Maximum tokens to generate, -1 for no limit
        provider: LLM provider to use (defaults to environment variable or OpenAI)

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
        provider=provider,
    )

    # Check cache for previous identical prompt
    previous_response = find_previous_response(request.prompt)
    if previous_response:
        logging.info(f"Using cached response for prompt: {prompt[:50]}...")
        return previous_response

    # Get the provider to use (either specified or default)
    provider_name = provider or os.getenv("DEFAULT_LLM_PROVIDER", "openai")

    # For backward compatibility with existing code
    if not provider_name or provider_name == "openai":
        try:
            # Prepare messages for the API call
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            # Make the API call with appropriate parameters
            if max_tokens == -1:
                response = openai.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                )
            else:
                response = openai.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                )

            # Extract and store the response
            response_text = response.choices[0].message.content
            store_response(prompt, response_text, model, "openai")
            return response_text
        except Exception as e:
            # If OpenAI call fails, try the new architecture as fallback
            logging.error(f"Error during OpenAI API call: {e}")

    # Use the new provider architecture
    try:
        # Generate the completion using the LLMClient
        response_text = LLMClient.complete(request)

        if response_text:
            # Store the successful response
            effective_provider = provider or LLMClient._default_provider
            store_response(prompt, response_text, model, effective_provider)

        return response_text
    except Exception as e:
        logging.error(f"Error during {provider or 'default'} LLM API call: {e}")
        return None


def main():
    """
    Demonstrate the functionality of the LLM module.

    This function shows practical examples of each capability in the module,
    including making API calls to different providers, caching, and post-processing responses.
    """
    # Set up OpenAI API key (normally this would be in environment variables)
    # openai.api_key = "your-api-key-here"  # Uncomment and set your API key

    print("=" * 50)
    print("LLM Module Demonstration")
    print("=" * 50)

    # Example 1: Simple LLM completion
    print("\n1. Simple LLM Completion (simulated)")

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
    store_response(mock_prompt, mock_response, "mock-gpt-4", "openai")
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
