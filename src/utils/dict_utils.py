# /src/utils/dict_utils.py

"""
Dictionary utilities for traversing, searching and filtering nested dictionaries.

This module provides functions to find paths to specific keys or key-value pairs
in nested dictionaries, and filter dictionaries based on those paths.
"""

from typing import Dict, List, Any, Optional, TypeVar, Union
from pydantic import BaseModel, Field
import json


T = TypeVar("T")
JsonDict = Dict[str, Any]
PathList = List[Union[str, int]]


class PathSpec(BaseModel):
    """Represents a path to a specific element in a nested dictionary."""

    path: PathList = Field(
        default_factory=list,
        description="Path to a specific element (list of keys/indices to traverse)",
    )


class KeySearchOptions(BaseModel):
    """Options for key search operations."""

    target_key: str = Field(description="The key to search for in the dictionary")


class KeyValueSearchOptions(KeySearchOptions):
    """Options for key-value pair search operations."""

    target_value: Any = Field(
        description="The value to search for associated with the target key"
    )


class FilterResult(BaseModel):
    """Result of a dictionary filtering operation."""

    filtered_dict: Optional[JsonDict] = Field(
        default=None,
        description="The filtered dictionary or None if no match was found",
    )


def find_key_val_path(
    d: JsonDict, target_key: str, target_val: Any
) -> Optional[PathList]:
    """
    Find the path to a specific key-value pair in a nested dictionary.

    Args:
        d: The dictionary to search in
        target_key: The key to search for
        target_val: The value associated with the key to match

    Returns:
        A list representing the path to the key-value pair, or None if not found

    Examples:
        >>> data = {"a": {"b": {"c": "value"}}}
        >>> find_key_val_path(data, "c", "value")
        ['a', 'b', 'c']
    """
    # Check if the target key exists at the current level and contains the target value
    if (
        target_key in d
        and isinstance(d[target_key], (str, list))
        and target_val in d[target_key]
    ):
        return [target_key]

    # Recursively search in nested dictionaries
    for key, value in d.items():
        if isinstance(value, dict):
            path = find_key_val_path(value, target_key, target_val)
            if path:
                return [key] + path
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    path = find_key_val_path(item, target_key, target_val)
                    if path:
                        return [key, index] + path
    return None


def find_key_path(d: JsonDict, target_key: str) -> Optional[PathList]:
    """
    Find the path to a specific key in a nested dictionary.

    Args:
        d: The dictionary to search in
        target_key: The key to search for

    Returns:
        A list representing the path to the key, or None if not found

    Examples:
        >>> data = {"a": {"b": {"c": "value"}}}
        >>> find_key_path(data, "c")
        ['a', 'b', 'c']
    """
    # Check if the target key exists at the current level
    if target_key in d:
        return [target_key]

    # Recursively search in nested dictionaries
    for key, value in d.items():
        if isinstance(value, dict):
            path = find_key_path(value, target_key)
            if path:
                return [key] + path
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    path = find_key_path(item, target_key)
                    if path:
                        return [key, index] + path
    return None


def filter_dict(d: JsonDict, path: PathList) -> Optional[JsonDict]:
    """
    Filter a dictionary by extracting a nested subset based on a path.

    Args:
        d: The dictionary to filter
        path: A list representing the path to the target nested dictionary

    Returns:
        A filtered dictionary containing only the specified path, or None if path doesn't exist

    Examples:
        >>> data = {"a": {"b": {"c": "value"}}}
        >>> filter_dict(data, ['a', 'b'])
        {'a': {'b': {'c': 'value'}}}
    """
    if not path:
        return None

    current_key = path[0]
    if current_key in d:
        if len(path) == 1:
            return {current_key: d[current_key]}
        elif isinstance(d[current_key], dict):
            nested_filtered = filter_dict(d[current_key], path[1:])
            if nested_filtered:
                return {current_key: nested_filtered}
        elif (
            isinstance(d[current_key], list)
            and len(path) > 1
            and isinstance(path[1], int)
        ):
            index = path[1]
            if 0 <= index < len(d[current_key]) and isinstance(
                d[current_key][index], dict
            ):
                nested_filtered = filter_dict(d[current_key][index], path[2:])
                if nested_filtered:
                    return {current_key: [nested_filtered]}
    return None


def filter_dict_by_key_val(d: JsonDict, target_key: str, target_val: Any) -> JsonDict:
    """
    Filter a dictionary by finding a specific key-value pair and returning the path to it.

    Args:
        d: The dictionary to filter
        target_key: The key to search for
        target_val: The value associated with the key to match

    Returns:
        A filtered dictionary containing the path to the key-value pair,
        or an empty dictionary if not found

    Examples:
        >>> data = {"a": {"b": {"c": "value"}}}
        >>> filter_dict_by_key_val(data, "c", "value")
        {'a': {'b': {'c': 'value'}}}
    """
    path = find_key_val_path(d, target_key, target_val)
    if not path:
        return {}
    result = filter_dict(d, path)
    return result if result else {}


def filter_dict_by_key(d: JsonDict, target_key: str) -> JsonDict:
    """
    Filter a dictionary by finding a specific key and returning the path to it.

    Args:
        d: The dictionary to filter
        target_key: The key to search for

    Returns:
        A filtered dictionary containing the path to the key,
        or an empty dictionary if not found

    Examples:
        >>> data = {"a": {"b": {"c": "value"}}}
        >>> filter_dict_by_key(data, "c")
        {'a': {'b': {'c': 'value'}}}
    """
    path = find_key_path(d, target_key)
    if not path:
        return {}
    result = filter_dict(d, path)
    return result if result else {}


def deep_get(d: JsonDict, path: PathList) -> Optional[Any]:
    """
    Access a nested element in a dictionary by path.

    Args:
        d: The dictionary to traverse
        path: A list representing the path to the target element

    Returns:
        The value at the specified path, or None if path doesn't exist

    Examples:
        >>> data = {"a": {"b": {"c": "value"}}}
        >>> deep_get(data, ['a', 'b', 'c'])
        'value'
    """
    if not path:
        return d

    current = d
    for key in path:
        if isinstance(current, dict) and key in current:
            current = current[key]
        elif (
            isinstance(current, list)
            and isinstance(key, int)
            and 0 <= key < len(current)
        ):
            current = current[key]
        else:
            return None
    return current


def is_subset(subset: JsonDict, superset: JsonDict) -> bool:
    """
    Check if one dictionary is a subset of another.

    Args:
        subset: The potential subset dictionary
        superset: The potential superset dictionary

    Returns:
        True if subset is contained within superset, False otherwise

    Examples:
        >>> is_subset({"a": 1}, {"a": 1, "b": 2})
        True
    """
    for key, value in subset.items():
        if key not in superset:
            return False

        if isinstance(value, dict) and isinstance(superset[key], dict):
            if not is_subset(value, superset[key]):
                return False
        elif isinstance(value, list) and isinstance(superset[key], list):
            # Simple list comparison - may need enhancement for complex cases
            if not all(item in superset[key] for item in value):
                return False
        elif value != superset[key]:
            return False

    return True


def main():
    """
    Demonstrate the usage of dictionary utilities.

    This function shows practical examples of using the utilities
    with a nested dictionary structure.
    """
    # Create a sample nested dictionary
    sample_data = {
        "person": {
            "name": "John Doe",
            "age": 30,
            "contact": {"email": "john@example.com", "phone": "123-456-7890"},
            "addresses": [
                {
                    "type": "home",
                    "street": "123 Main St",
                    "city": "Anytown",
                    "tags": ["primary", "residential"],
                },
                {
                    "type": "work",
                    "street": "456 Office Blvd",
                    "city": "Workville",
                    "tags": ["business"],
                },
            ],
        },
        "preferences": {"notifications": True, "theme": "dark"},
    }

    print("Original Dictionary:")
    print(json.dumps(sample_data, indent=2))
    print("\n" + "=" * 50 + "\n")

    # Example 1: Find key path
    key = "email"
    path = find_key_path(sample_data, key)
    print(f"Path to key '{key}': {path}")
    value = deep_get(sample_data, path) if path else None
    print(f"Value at path: {value}")
    print("\n" + "-" * 30 + "\n")

    # Example 2: Find key-value path
    key = "tags"
    val = "primary"
    path = find_key_val_path(sample_data, key, val)
    print(f"Path to '{key}' with value containing '{val}': {path}")
    value = deep_get(sample_data, path) if path else None
    print(f"Value at path: {value}")
    print("\n" + "-" * 30 + "\n")

    # Example 3: Filter dictionary by key
    key = "contact"
    filtered = filter_dict_by_key(sample_data, key)
    print(f"Dictionary filtered by key '{key}':")
    print(json.dumps(filtered, indent=2))
    print("\n" + "-" * 30 + "\n")

    # Example 4: Filter dictionary by path
    path = ["person", "addresses", 0]
    filtered = filter_dict(sample_data, path)
    print(f"Dictionary filtered by path {path}:")
    print(json.dumps(filtered, indent=2))
    print("\n" + "-" * 30 + "\n")

    # Example 5: Filter dictionary by key-value pair
    key = "theme"
    val = "dark"
    filtered = filter_dict_by_key_val(sample_data, key, val)
    print(f"Dictionary filtered by key '{key}' with value '{val}':")
    print(json.dumps(filtered, indent=2))
    print("\n" + "=" * 50 + "\n")

    # Example 6: Check if one dict is subset of another
    subset = {"person": {"name": "John Doe"}}
    result = is_subset(subset, sample_data)
    print(f"Is {json.dumps(subset)} a subset of the original dictionary? {result}")

    # Create Pydantic models from our functions
    search_options = KeySearchOptions(target_key="email")
    print(f"\nPydantic model for search options: {search_options.model_dump()}")

    path_spec = PathSpec(path=["person", "contact", "email"])
    print(f"Pydantic model for path specification: {path_spec.model_dump()}")


if __name__ == "__main__":
    main()
