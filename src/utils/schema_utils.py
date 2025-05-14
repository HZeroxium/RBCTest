# /src/utils/schema_utils.py

"""
Schema Utilities

This module provides functions for working with OpenAPI schemas, including
filtering, validation, and comparison operations.
"""

from typing import Dict, List, Any, Optional, Union, Set
import copy
import json


def standardize_string(string: str) -> str:
    """
    Standardize a string by stripping whitespace and removing quotes.

    Args:
        string: The string to standardize

    Returns:
        Standardized string
    """
    return string.strip().replace('"', "").replace("'", "")


def get_data_type(attr_simplified_spec: str) -> str:
    """
    Extract the data type from a simplified attribute specification.

    Args:
        attr_simplified_spec: Simplified attribute specification

    Returns:
        The data type portion of the specification
    """
    return attr_simplified_spec.split("(description:")[0].strip()


def filter_attributes_in_schema_by_data_type(
    schema_spec: Union[Dict[str, Any], List[Any], str], filtering_data_type: str
) -> Union[Dict[str, Any], List[Any], str, None]:
    """
    Filter attributes in a schema to include only those with a specific data type.

    This function recursively filters through a schema specification and keeps only
    attributes that match the specified data type.

    Args:
        schema_spec: Schema specification to filter (can be dict, list, or string)
        filtering_data_type: Data type to filter by (e.g., "string", "integer")

    Returns:
        Filtered schema with only attributes matching the specified data type
    """
    # Handle string case first (base case for recursion)
    if isinstance(schema_spec, str):
        data_type = schema_spec.split("(description:")[0].strip()
        if data_type != filtering_data_type:
            return {}
        return schema_spec

    # Handle empty case
    if not schema_spec:
        return {}

    # Handle dictionary case
    if isinstance(schema_spec, dict):
        specification = copy.deepcopy(schema_spec)
        for attribute, value in schema_spec.items():
            if isinstance(value, dict):
                filtered_value = filter_attributes_in_schema_by_data_type(
                    value, filtering_data_type
                )
                if not filtered_value:
                    del specification[attribute]
                    continue
                specification[attribute] = filtered_value
            elif isinstance(value, list):
                filtered_value = (
                    filter_attributes_in_schema_by_data_type(
                        value[0], filtering_data_type
                    )
                    if value
                    else {}
                )
                if not filtered_value:
                    del specification[attribute]
                    continue
                specification[attribute] = [filtered_value]
            elif isinstance(value, str):
                data_type = value.split("(description:")[0].strip()
                if data_type != filtering_data_type:
                    del specification[attribute]
        return specification

    # Handle list case
    if isinstance(schema_spec, list) and schema_spec:
        return [
            filter_attributes_in_schema_by_data_type(item, filtering_data_type)
            for item in schema_spec
            if filter_attributes_in_schema_by_data_type(item, filtering_data_type)
        ]

    # Default case
    return {}


def verify_attribute_in_schema(
    schema_spec: Union[Dict[str, Any], List[Any], str], attribute: str
) -> bool:
    """
    Check if an attribute exists in a schema specification.

    This function recursively searches through a schema to find a specific attribute.

    Args:
        schema_spec: Schema specification to search in
        attribute: Attribute name to search for

    Returns:
        True if the attribute is found, False otherwise
    """
    if isinstance(schema_spec, dict):
        for key, value in schema_spec.items():
            if key == attribute:
                return True
            if isinstance(value, dict):
                if verify_attribute_in_schema(value, attribute):
                    return True
            if isinstance(value, list):
                if value and verify_attribute_in_schema(value[0], attribute):
                    return True
    return False


def find_common_fields(json1: Dict[str, Any], json2: Dict[str, Any]) -> List[str]:
    """
    Find fields that are common between two JSON objects.

    Args:
        json1: First JSON object
        json2: Second JSON object

    Returns:
        List of field names that appear in both objects
    """
    common_fields = []
    for key in json1.keys():
        if key in json2.keys():
            common_fields.append(key)
    return common_fields


def filter_schema_attributes_by_data_type(
    schema_spec: Dict[str, Any], target_data_types: Union[List[str], Set[str], str]
) -> Dict[str, Any]:
    """
    Filter schema attributes to only include those of specified data types.

    Args:
        schema_spec: Schema specification to filter
        target_data_types: Target data type(s) to keep, either a single string or a collection

    Returns:
        Filtered schema containing only attributes of the specified data type(s)
    """
    if isinstance(target_data_types, str):
        target_data_types = {target_data_types}
    elif isinstance(target_data_types, list):
        target_data_types = set(target_data_types)

    result = {}

    for attr, value in schema_spec.items():
        if isinstance(value, str):
            data_type = value.split("(description:")[0].strip()
            if data_type in target_data_types:
                result[attr] = value
        else:
            # Skip non-string attributes
            pass

    return result
