"""
Core OpenAPI specification utilities for loading and basic operations.

This module provides fundamental functions for loading and parsing OpenAPI specifications.
"""

import os
import json
import yaml
from typing import Dict, List, Any, Optional, Union


def ruler() -> None:
    """Print a horizontal ruler line of dashes to the console."""
    print("-" * 100)


def jprint(x: Any) -> None:
    """
    Print the given JSON-serializable object with nice formatting.

    Args:
        x: Any JSON-serializable object to print
    """
    print(json.dumps(x, indent=2))


def success_code(x: int) -> bool:
    """
    Check if an HTTP status code represents success (2xx).

    Args:
        x: HTTP status code to check

    Returns:
        True if the code is in the 2xx range, False otherwise
    """
    return 200 <= x < 300


def convert_path_fn(x: str) -> str:
    """
    Convert an API path to a valid filename by replacing special characters.

    Args:
        x: API path string

    Returns:
        Path string with '/', '{', '}', '.' characters replaced with underscores
    """
    return re.sub(r"_+", "_", re.sub(r"[\/{}.]", "_", x))


def isSuccessStatusCode(x: Union[int, str]) -> bool:
    """
    Check if a status code represents a successful HTTP response.

    Args:
        x: Status code as integer or string

    Returns:
        True if the status code is in the 2xx range
    """
    if isinstance(x, int):
        return success_code(x)
    elif isinstance(x, str):
        return x.isdigit() and success_code(int(x))
    return False


def load_openapi(path: str) -> Optional[Dict[str, Any]]:
    """
    Load an OpenAPI specification from a file.

    Supports both YAML and JSON formats.

    Args:
        path: Path to the OpenAPI specification file

    Returns:
        Parsed OpenAPI specification as a dictionary or None if loading fails
    """
    # Check if file exists
    if not os.path.exists(path):
        print(f"File {path} is not existed")
        return None

    if path.endswith(".yml") or path.endswith(".yaml"):
        # Read YAML file
        with open(path, "r") as stream:
            try:
                return yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)

    elif path.endswith(".json"):
        # Read JSON file
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        print(f"File {path} is not supported. Must be in YAML or JSON format.")
        return None


def get_ref(spec: Dict[str, Any], ref: str) -> Dict[str, Any]:
    """
    Resolve a JSON reference in an OpenAPI specification.

    Args:
        spec: OpenAPI specification dictionary
        ref: Reference string (e.g., "#/components/schemas/User")

    Returns:
        The referenced object
    """
    sub = ref[2:].split("/")
    schema = spec
    for e in sub:
        schema = schema.get(e, {})
    return schema


def find_object_with_key(json_obj: Any, target_key: str) -> Optional[Dict[str, Any]]:
    """
    Find the first object in a nested structure that contains the specified key.

    Args:
        json_obj: Object to search in (can be dict, list, or other types)
        target_key: Key to search for

    Returns:
        The first object containing the target key, or None if not found
    """
    if isinstance(json_obj, dict):
        if target_key in json_obj:
            return json_obj
        for value in json_obj.values():
            result = find_object_with_key(value, target_key)
            if result is not None:
                return result
    elif isinstance(json_obj, list):
        for item in json_obj:
            result = find_object_with_key(item, target_key)
            if result is not None:
                return result
    return None


def extract_operations(spec: Dict[str, Any]) -> List[str]:
    """
    Extract all API operations from an OpenAPI specification.

    Each operation is returned as a string in the format "{method}-{path}".

    Args:
        spec: OpenAPI specification dictionary

    Returns:
        List of operation strings
    """
    operations = []
    paths = spec["paths"]
    valid_methods = [
        "get",
        "post",
        "put",
        "delete",
        "patch",
        "head",
        "options",
        "trace",
    ]
    for path in paths:
        for method in paths[path]:
            if method.startswith("x-") or method not in valid_methods:
                continue
            operations.append(method + "-" + path)

    return operations


def extract_ref_values(json_obj: Any) -> List[str]:
    """
    Extract all $ref values from a nested JSON object.

    Args:
        json_obj: JSON object to search in

    Returns:
        List of unique $ref values found
    """
    refs = []

    if isinstance(json_obj, dict):
        for key, value in json_obj.items():
            if key == "$ref":
                refs.append(value)
            else:
                refs.extend(extract_ref_values(value))
    elif isinstance(json_obj, list):
        for item in json_obj:
            refs.extend(extract_ref_values(item))

    return list(set(refs))


# Need to import re which was missing in the original file
import re
