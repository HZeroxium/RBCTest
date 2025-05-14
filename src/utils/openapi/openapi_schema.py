# /src/utils/openapi/openapi_schema.py

"""
OpenAPI schema utilities for working with schema objects and definitions.

This module provides functions for extracting, processing, and analyzing
schema information from OpenAPI specifications.
"""

import copy
from typing import Dict, List, Any, Optional, Set, Tuple, Union

from .openapi_core import get_ref, find_object_with_key, extract_ref_values


def get_schema_params(
    body: Dict[str, Any],
    spec: Dict[str, Any],
    visited_refs: Optional[Set[str]] = None,
    get_description: bool = False,
    max_depth: Optional[int] = None,
    current_depth: int = 0,
    ignore_attr_with_schema_ref: bool = False,
) -> Optional[Union[Dict[str, Any], str]]:
    """
    Extract schema parameters from an OpenAPI schema object.

    This function recursively processes a schema object and extracts its structure,
    potentially including descriptions.

    Args:
        body: Schema object to process
        spec: Complete OpenAPI specification containing reference definitions
        visited_refs: Set of already visited references to prevent infinite recursion
        get_description: Whether to include descriptions in the output
        max_depth: Maximum recursion depth (None for unlimited)
        current_depth: Current recursion depth
        ignore_attr_with_schema_ref: Whether to ignore attributes that have schema references

    Returns:
        Processed schema as a dict or string, or None if processing cannot be completed
    """
    if visited_refs is None:
        visited_refs = set()

    if max_depth is not None:
        if current_depth > max_depth:
            return None

    properties = find_object_with_key(body, "properties")
    ref = find_object_with_key(body, "$ref")
    schema = find_object_with_key(body, "schema")

    new_schema = {}
    if properties:
        for p, prop_details in properties["properties"].items():
            p_ref = find_object_with_key(prop_details, "$ref")

            if p_ref and ignore_attr_with_schema_ref:
                continue

            # Initialize the description string
            description_string = ""

            # Check the get_description flag
            if get_description:
                description_parent = find_object_with_key(prop_details, "description")
                if description_parent and not isinstance(
                    description_parent["description"], dict
                ):
                    description_string = (
                        " (description: "
                        + description_parent["description"].strip(" .")
                        + ")"
                    )

            if "type" in prop_details:
                if prop_details["type"] == "array":
                    if p_ref:
                        new_schema[p] = {}
                        new_schema[p][
                            f'array of \'{p_ref["$ref"].split("/")[-1]}\' objects'
                        ] = [
                            get_schema_params(
                                prop_details,
                                spec,
                                visited_refs=visited_refs,
                                get_description=get_description,
                                max_depth=max_depth,
                                current_depth=current_depth + 1,
                            )
                        ]
                    else:
                        new_schema[p] = {}
                        new_schema[p][
                            f'array of {prop_details["items"]["type"]} objects'
                        ] = [
                            get_schema_params(
                                prop_details["items"],
                                spec,
                                visited_refs=visited_refs,
                                get_description=get_description,
                                max_depth=max_depth,
                                current_depth=current_depth + 1,
                            )
                        ]
                else:
                    new_schema[p] = prop_details["type"] + description_string

            elif p_ref:
                if p_ref["$ref"] in visited_refs:
                    new_schema[p] = {f'schema of {p_ref["$ref"].split("/")[-1]}': {}}
                    continue

                visited_refs.add(p_ref["$ref"])
                schema = get_ref(spec, p_ref["$ref"])
                child_schema = get_schema_params(
                    schema,
                    spec,
                    visited_refs=visited_refs,
                    get_description=get_description,
                    max_depth=max_depth,
                    current_depth=current_depth + 1,
                )
                if child_schema is not None:
                    new_schema[p] = {}
                    new_schema[p][
                        f'schema of {p_ref["$ref"].split("/")[-1]}'
                    ] = child_schema

    elif ref:
        if ref["$ref"] in visited_refs:
            return None

        visited_refs.add(ref["$ref"])
        schema = get_ref(spec, ref["$ref"])
        new_schema = get_schema_params(
            schema,
            spec,
            visited_refs=visited_refs,
            get_description=get_description,
            max_depth=max_depth,
            current_depth=current_depth + 1,
        )
    elif schema:
        return get_schema_params(
            schema["schema"],
            spec,
            visited_refs=visited_refs,
            get_description=get_description,
            max_depth=max_depth,
            current_depth=current_depth + 1,
        )
    else:
        field_value = ""
        if body is not None and "type" in body:
            field_value = body["type"]

        if field_value != "":
            return field_value
        else:
            return None

    return new_schema


def get_schema_required_fields(
    body: Dict[str, Any], spec: Dict[str, Any], visited_refs: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Extract the required fields from a schema object.

    This function processes a schema and returns only the required fields
    based on the 'required' property.

    Args:
        body: Schema object to process
        spec: Complete OpenAPI specification
        visited_refs: Set of already visited references to prevent infinite recursion

    Returns:
        Dictionary containing only the required fields
    """
    if visited_refs is None:
        visited_refs = set()

    properties = find_object_with_key(body, "properties")
    ref = find_object_with_key(body, "$ref")
    schema = find_object_with_key(body, "schema")

    required_fields = []
    required_fields_spec = find_object_with_key(body, "required")
    if required_fields_spec is None:
        if properties is not None:
            return {}
    else:
        required_fields = required_fields_spec["required"]

    new_schema = {}
    if properties:
        for p, prop_details in properties["properties"].items():
            if p not in required_fields:
                continue

            p_ref = find_object_with_key(prop_details, "$ref")

            if "type" in prop_details:
                if prop_details["type"] == "array":
                    if p_ref:
                        new_schema[p] = {}
                        new_schema[p] = get_schema_required_fields(
                            prop_details, spec, visited_refs=visited_refs
                        )
                    else:
                        new_schema[p] = "array"
                else:
                    new_schema[p] = prop_details["type"]

            elif p_ref:
                if p_ref["$ref"] in visited_refs:
                    continue

                visited_refs.add(p_ref["$ref"])
                schema = get_ref(spec, p_ref["$ref"])
                child_schema = get_schema_required_fields(
                    schema, spec, visited_refs=visited_refs
                )
                if child_schema is not None:
                    new_schema[p] = child_schema

    elif ref:
        if ref["$ref"] in visited_refs:
            return {}

        visited_refs.add(ref["$ref"])
        schema = get_ref(spec, ref["$ref"])
        new_schema = get_schema_required_fields(schema, spec, visited_refs=visited_refs)
    else:
        return {}

    return new_schema


def get_schema_recursive(
    body: Dict[str, Any], spec: Dict[str, Any], visited_refs: Optional[Set[str]] = None
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Recursively extract schemas from references within a schema object.

    This function walks through all references in a schema and extracts the
    referenced schemas.

    Args:
        body: Schema object to process
        spec: Complete OpenAPI specification
        visited_refs: Set of already visited references to prevent infinite recursion

    Returns:
        Tuple of (schema_dict, schema_name_list) where:
          - schema_dict: Dictionary mapping schema names to their definitions
          - schema_name_list: List of schema names found
    """
    if visited_refs is None:
        visited_refs = set()

    schema_dict = {}
    schema_name_list = []
    schema_refs = extract_ref_values(body)

    for ref in schema_refs:
        schema_name = ref.split("/")[-1]

        if ref not in visited_refs:  # Check if schema_name is already processed
            visited_refs.add(ref)

            schema_body = get_ref(spec, ref)

            new_schema = get_schema_params(
                schema_body,
                spec,
                get_description=True,
                max_depth=0,
                ignore_attr_with_schema_ref=False,
            )
            if isinstance(new_schema, dict):
                schema_dict[schema_name] = new_schema
                schema_name_list.append(schema_name)  # Add schema_name only if it's new

            nested_schemas_body, nested_schemas_name = get_schema_recursive(
                schema_body, spec, visited_refs=visited_refs
            )
            schema_dict.update(nested_schemas_body)
            schema_name_list.extend(nested_schemas_name)

    return schema_dict, schema_name_list


def get_simplified_schema(spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract simplified schema definitions from an OpenAPI specification.

    This function extracts all schemas referenced in the success responses of
    the API operations and simplifies them.

    Args:
        spec: OpenAPI specification dictionary

    Returns:
        Dictionary mapping schema names to their simplified definitions
    """
    from .openapi_operations import extract_operations, is_success_status_code

    simplified_schema_dict = {}

    operations = extract_operations(spec)

    for operation in operations:
        method = operation.split("-")[0]
        object_name = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(spec["paths"][object_name][method])

        # responseBody (single response body)
        if "responses" in obj:
            responses = obj["responses"]
            success_response = None
            for rk, rv in responses.items():
                if is_success_status_code(rk):
                    success_response = rv

                    schema_ref = find_object_with_key(success_response, "$ref")
                    if schema_ref is None:
                        continue

                    simplified_schema, _ = get_schema_recursive(success_response, spec)
                    simplified_schema_dict.update(simplified_schema)

    return simplified_schema_dict


def list_all_param_names(
    spec: Dict[str, Any], d: Dict[str, Any], visited_refs: Optional[Set[str]] = None
) -> List[str]:
    """
    Extract all parameter names from a schema definition.

    This function recursively extracts all parameter names from a schema object.

    Args:
        spec: OpenAPI specification dictionary
        d: Schema object to process
        visited_refs: Set of already visited references to prevent infinite recursion

    Returns:
        List of parameter names
    """
    if visited_refs is None:
        visited_refs = set()

    if d is None:
        return []

    if "$ref" in d:
        ref = d["$ref"]
        if ref in visited_refs:
            return []
        visited_refs.add(ref)
        return list_all_param_names(spec, get_ref(spec, ref), visited_refs)

    if d.get("type") == "object":
        res = list(d.get("properties", {}).keys())
        for val in d.get("properties", {}).values():
            res += list_all_param_names(spec, val, visited_refs)
        return res
    elif d.get("type") == "array":
        return list_all_param_names(spec, d.get("items", {}), visited_refs)
    elif "name" in d:
        return [d.get("name")]
    else:
        return []
