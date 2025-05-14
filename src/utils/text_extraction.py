# /src/utils/text_extraction.py

"""
Text Extraction Utilities

This module provides functions for extracting specific information from text,
particularly focused on parsing structured text content like code blocks,
constraints, and variables from natural language descriptions.
"""

import re
import json
from typing import List, Optional, Set, Dict, Any, Union, Tuple


def extract_variables(statement: str) -> List[str]:
    """
    Extract variables from a statement or code snippet.

    This function identifies potential variable names in a string by finding
    words that match variable naming patterns while excluding known keywords.

    Args:
        statement: String containing potential variable names

    Returns:
        List of identified variables names

    Examples:
        >>> extract_variables("if x > 10 and y < 20:")
        ['x', 'y']
    """
    variable_pattern = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"
    matches = re.findall(variable_pattern, statement)

    keywords = {
        "IF",
        "THEN",
        "Or",
        "OnlyOne",
        "AllOrNone",
        "ZeroOrOne",
        "AND",
        "OR",
        "NOT",
        "==",
        "!=",
        "<=",
        "<",
        ">=",
        ">",
        "+",
        "-",
        "*",
        "/",
        "True",
        "False",
        "true",
        "false",
    }

    variables = []
    for match in matches:
        if match not in keywords:
            preceding_text = statement[: statement.find(match)]
            if not (
                preceding_text.count('"') % 2 != 0 or preceding_text.count("'") % 2 != 0
            ):
                variables.append(match)

    return list(set(variables))


def extract_values(statement: str) -> List[str]:
    """
    Extract literal values from a statement or code snippet.

    This function finds string literals (in single or double quotes) and numeric literals.

    Args:
        statement: String containing potential literal values

    Returns:
        List of identified literal values

    Examples:
        >>> extract_values("age = 30 and name = 'John'")
        ['30', 'John']
    """
    pattern = r"\'(.*?)\'|\"(.*?)\"|(\d+\.?\d*)"
    matches = re.findall(pattern, statement)

    values = [match[0] or match[1] or match[2] for match in matches]
    return values


def extract_dict_attributes(
    input_dict: Dict[str, Any], keys_list: Optional[List[str]] = None
) -> List[str]:
    """
    Recursively extract attribute names from a nested dictionary.

    This function extracts all keys from a dictionary, excluding those that
    start with "array of" or "schema of", which are typically OpenAPI schema markers.

    Args:
        input_dict: Dictionary to extract keys from
        keys_list: Optional list to accumulate keys (used for recursive calls)

    Returns:
        List of key names from the dictionary hierarchy

    Examples:
        >>> data = {"name": "John", "address": {"city": "New York", "zip": 10001}}
        >>> extract_dict_attributes(data)
        ['name', 'address', 'city', 'zip']
    """
    if keys_list is None:
        keys_list = []

    for key, value in input_dict.items():
        if not key.startswith("array of") and not key.startswith("schema of"):
            keys_list.append(key)
        if isinstance(value, dict):
            extract_dict_attributes(value, keys_list)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    extract_dict_attributes(item, keys_list)
    return keys_list


def extract_python_code(response: Optional[str]) -> Optional[str]:
    """
    Extract Python code blocks from a string.

    This function finds Python code blocks delimited by triple backticks and "python".

    Args:
        response: String containing potential Python code blocks

    Returns:
        Extracted Python code or None if no code blocks were found

    Examples:
        >>> code = extract_python_code("Here's some code: ```python\\ndef hello():\\n    print('Hello')\\n```")
        >>> code
        "def hello():\\n    print('Hello')"
    """
    if response is None:
        return None

    pattern = r"```python\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)

    if match:
        python_code = match.group(1)
        return python_code
    else:
        return None


def extract_answer(response: Optional[str]) -> Optional[str]:
    """
    Extract an answer from a response string.

    This function finds content between ```answer and ``` markers, or returns
    the lowercased response if no markers are found.

    Args:
        response: String containing a potential answer section

    Returns:
        Extracted answer or None if the response is None

    Examples:
        >>> extract_answer("Here's my answer: ```answer\\nYes, the constraint is valid.\\n```")
        'yes, the constraint is valid.'
    """
    if response is None:
        return None

    if "```answer" in response:
        pattern = r"```answer\n(.*?)```"
        match = re.search(pattern, response, re.DOTALL)

        if match:
            answer = match.group(1)
            return answer.strip()
        else:
            return None
    else:
        return response.lower()


def extract_summary_constraint(response: Optional[str]) -> Optional[str]:
    """
    Extract a constraint summary from a response string.

    This function finds content between ```constraint and ``` markers.

    Args:
        response: String containing a potential constraint section

    Returns:
        Extracted constraint or None if none was found

    Examples:
        >>> extract_summary_constraint("Here is the constraint: ```constraint\\nvalue must be > 0\\n```")
        'value must be > 0'
    """
    if response is None:
        return None

    pattern = r"```constraint\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)

    if match:
        constraint = match.group(1)
        return constraint.strip()
    else:
        return None


def extract_idl(response: Optional[str]) -> Optional[str]:
    """
    Extract Interface Definition Language (IDL) content from a response string.

    This function finds content between ```IDL and ``` markers.

    Args:
        response: String containing potential IDL section

    Returns:
        Extracted IDL content or None if none was found

    Examples:
        >>> extract_idl("Here's the IDL: ```IDL\\ninterface User { name: string; }\\n```")
        'interface User { name: string; }'
    """
    if response is None:
        return None

    pattern = r"```IDL\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)

    if match:
        constraint = match.group(1)
        return constraint.strip()
    else:
        return None


def is_construct_json_object(text: str) -> bool:
    """
    Check if a string can be parsed as a valid JSON object.

    Args:
        text: String to validate as JSON

    Returns:
        True if the string is valid JSON, False otherwise

    Examples:
        >>> is_construct_json_object('{"name": "John", "age": 30}')
        True
        >>> is_construct_json_object('Not a JSON string')
        False
    """
    try:
        json.loads(text)
        return True
    except:
        return False


def standardize_returned_idl(idl_sentence: Optional[str]) -> Optional[str]:
    """
    Standardize an IDL sentence by removing prefixes and unnecessary characters.

    This function processes each line of an IDL definition to clean it up.

    Args:
        idl_sentence: IDL text to standardize

    Returns:
        Standardized IDL text, or None if input was None

    Examples:
        >>> standardize_returned_idl("Definition: interface User { name: string; }")
        'interface User { name: string; }'
    """
    if idl_sentence is None:
        return None

    idl_lines = idl_sentence.split("\n")
    for i, line in enumerate(idl_lines):
        if ":" in line:
            idl_lines[i] = line.split(":", 1)[1].lstrip()

    result = "\n".join(idl_lines).strip("`\"'")

    return result


def extract_structured_field(response: Optional[str], field_name: str) -> Optional[str]:
    """
    Generic function to extract content between ```field_name and ``` markers.

    Args:
        response: String containing potential marked sections
        field_name: The name of the field to extract

    Returns:
        Extracted field content or None if none was found

    Examples:
        >>> extract_structured_field("Here's some data: ```json\\n{\"key\": \"value\"}\\n```", "json")
        '{\"key\": \"value\"}'
    """
    if response is None:
        return None

    pattern = rf"```{field_name}\n(.*?)```"
    match = re.search(pattern, response, re.DOTALL)

    if match:
        content = match.group(1)
        return content.strip()
    else:
        return None


def extract_data_model_key_pairs(response: str) -> List[Tuple[str, str]]:
    """
    Extract field mapping pairs from a data model response.

    This function parses responses that contain field mapping relationships
    in the format "field1 -> field2".

    Args:
        response: String response containing field mapping relationships

    Returns:
        List of tuples containing the field pairs (source_field, target_field)
    """
    pattern = r"(\w+) -> (\w+)"
    matches = re.findall(pattern, response)

    key_pairs = [
        (match[0], match[1])
        for match in matches
        if match[0] != "None" and match[1] != "None"
    ]

    return key_pairs
