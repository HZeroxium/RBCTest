# /src/utils/request_utils.py

"""
Request Utility Functions

This module provides utility functions for handling HTTP requests.
"""

import urllib.parse
import json
from typing import Dict, Any, Optional, Union


def is_valid_url(url: str) -> bool:
    """
    Check if a string is a valid URL.

    Args:
        url: String to check

    Returns:
        True if the string is a valid URL, False otherwise

    Examples:
        >>> is_valid_url("https://example.com")
        True
        >>> is_valid_url("not-a-url")
        False
    """
    parsed_url = urllib.parse.urlparse(url)
    return all([parsed_url.scheme, parsed_url.netloc])


def parse_request_info_from_query_parameters(query_parameters: str) -> str:
    """
    Parse query parameters string into a JSON string.

    Args:
        query_parameters: Query string in format "key1=value1&key2=value2&..."

    Returns:
        JSON string representation of the query parameters

    Examples:
        >>> parse_request_info_from_query_parameters("name=John&age=30")
        '{"name": "John", "age": "30"}'
    """
    request_info: Dict[str, str] = {}

    if query_parameters:
        parsed_params = urllib.parse.parse_qs(query_parameters)
        for key, value in parsed_params.items():
            request_info[key] = value[0]

    return json.dumps(request_info)
