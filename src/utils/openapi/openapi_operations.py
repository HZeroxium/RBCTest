"""
OpenAPI operations utilities for working with API operations.

This module provides functions for extracting, processing, and analyzing
operation information from OpenAPI specifications.
"""

import copy
from typing import Dict, List, Any, Optional, Tuple

from .openapi_core import (
    find_object_with_key,
    get_ref,
    isSuccessStatusCode,
    extract_operations,
    convert_path_fn,
)

from .openapi_schema import (
    get_schema_params,
    get_schema_required_fields,
    get_schema_recursive,
)


def get_operation_params(
    spec: Dict[str, Any],
    only_get_parameter_types: bool = False,
    get_not_required_params: bool = True,
    get_test_object: bool = False,
    insert_test_data_file_link: bool = False,
    get_description: bool = False,
    get_response_body: bool = True,
) -> Dict[str, Dict[str, Any]]:
    """
    Extract parameter information from all operations in an OpenAPI specification.

    This function extracts details about parameters, request bodies, and response bodies
    from all operations in the specification.

    Args:
        spec: OpenAPI specification dictionary
        only_get_parameter_types: If True, only extract the parameter types (e.g., PATH VARIABLE, QUERY PARAMETER)
        get_not_required_params: If True, include non-required parameters
        get_test_object: If True, include test objects
        insert_test_data_file_link: If True, insert links to test data files
        get_description: If True, include parameter descriptions
        get_response_body: If True, include response body information

    Returns:
        Dictionary mapping operation IDs to their parameter information
    """
    operations = extract_operations(spec)
    operation_params_only_dict = {}

    for operation in operations:
        method = operation.split("-")[0]
        object_name = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(spec["paths"][object_name][method])

        operation_params_only_entry = {}

        if "tags" in obj:
            operation_params_only_entry["tags"] = obj["tags"]
        if "summary" in obj:
            operation_params_only_entry["summary"] = obj["summary"]
        if "description" in obj:
            operation_params_only_entry["description"] = obj["description"]

        if get_test_object:
            if "test_object" in obj and obj["test_object"] is not None:
                operation_params_only_entry["test_object"] = obj["test_object"].strip(
                    "\n"
                )

        # parameters
        if "parameters" in obj and obj["parameters"]:
            if only_get_parameter_types == False:
                params = obj["parameters"]
                param_entry = {}

                if get_not_required_params:
                    for param in params:
                        if "$ref" in param:
                            param = get_ref(spec, param["$ref"])

                        # get description string
                        description_string = ""
                        if get_description:
                            description_parent = find_object_with_key(
                                param, "description"
                            )
                            if description_parent and not isinstance(
                                description_parent["description"], dict
                            ):
                                description_string = (
                                    " (description: "
                                    + description_parent["description"].strip(" .")
                                    + ")"
                                )

                        name, dtype = None, None
                        name_parent = find_object_with_key(param, "name")
                        type_parent = find_object_with_key(param, "type")
                        param_schema_parent = find_object_with_key(param, "$ref")

                        if name_parent:
                            name = name_parent["name"]
                        if type_parent:
                            dtype = type_parent["type"]

                        if name is not None and param_schema_parent is not None:
                            param_schema = get_ref(spec, param_schema_parent["$ref"])
                            param_entry[name] = get_schema_params(param_schema, spec)
                        elif name is not None and dtype is not None:
                            param_entry[name] = dtype + description_string
                else:
                    for param in params:
                        if "$ref" in param:
                            param = get_ref(spec, param["$ref"])

                        # get description string
                        description_string = ""
                        if get_description:
                            description_parent = find_object_with_key(
                                param, "description"
                            )
                            if description_parent and not isinstance(
                                description_parent["description"], dict
                            ):
                                description_string = (
                                    " (description: "
                                    + description_parent["description"].strip(" .")
                                    + ")"
                                )

                        name, dtype, required = None, None, None
                        name_parent = find_object_with_key(param, "name")
                        type_parent = find_object_with_key(param, "type")
                        param_schema_parent = find_object_with_key(param, "$ref")

                        required_parent = find_object_with_key(param, "required")
                        if name_parent:
                            name = name_parent["name"]
                        if type_parent:
                            dtype = type_parent["type"]

                        required = False
                        if required_parent:
                            required = required_parent["required"]

                        if required:
                            if name is not None and param_schema_parent is not None:
                                param_schema = get_ref(
                                    spec, param_schema_parent["$ref"]
                                )
                                param_entry[name] = get_schema_params(
                                    param_schema, spec
                                )
                            elif name is not None and dtype is not None:
                                param_entry[name] = dtype + description_string
            else:
                # In detailed parameters mode, we will return the whole parameters object instead of just the name and type
                # Only keep 'name' and 'in' field
                param_entry = {}
                for param in obj["parameters"]:
                    if "name" in param and "in" in param:
                        if param["in"] == "path":
                            param_entry[param["name"]] = "PATH VARIABLE"
                        else:
                            param_entry[param["name"]] = "QUERY PARAMETER"

            if param_entry:
                operation_params_only_entry["parameters"] = param_entry

        # requestBody
        if "requestBody" in obj:
            body_entry = {}

            schema_obj = find_object_with_key(obj["requestBody"], "schema")
            if schema_obj is not None:
                request_body_schema = schema_obj["schema"]
                if "$ref" in request_body_schema:
                    schema_name = request_body_schema["$ref"].split("/")[-1]
                    body_entry[f"schema of {schema_name}"] = get_schema_params(
                        request_body_schema, spec, get_description=get_description
                    )
                else:
                    body_entry = get_schema_params(
                        request_body_schema, spec, get_description=get_description
                    )

            if body_entry:
                operation_params_only_entry["requestBody"] = body_entry

        # responseBody (single response body)
        if get_response_body and ("responses" in obj or "response" in obj):
            response_entry = {}

            if method.lower() != "delete":
                if "responses" in obj:
                    responses = obj["responses"]
                else:
                    responses = obj["response"]

                success_response = None
                for rk, rv in responses.items():
                    if isSuccessStatusCode(rk):
                        success_response = rv
                        break

                if success_response is not None:
                    schema_object_ref = find_object_with_key(success_response, "$ref")

                    if schema_object_ref is not None:
                        schema_name = schema_object_ref["$ref"].split("/")[-1]
                        response_entry[f"schema of {schema_name}"] = get_schema_params(
                            success_response, spec, get_description=get_description
                        )
                    else:
                        response_entry = get_schema_params(
                            success_response, spec, get_description=get_description
                        )

                if response_entry:
                    operation_params_only_entry["responseBody"] = response_entry

        if insert_test_data_file_link:
            test_data = {}
            try:
                operation_id = spec["paths"][object_name][method]["operationId"]
            except:
                operation_id = method.upper()
            unique_name = f"{convert_path_fn(object_name)}_{operation_id}"

            if (
                "parameters" in obj
                and obj["parameters"]
                and operation_params_only_entry["parameters"] is not None
            ):
                test_data["Parameter data"] = f"Data Files/{unique_name}_param"

            if (
                "requestBody" in obj
                and obj["requestBody"]
                and operation_params_only_entry["requestBody"] is not None
            ):
                test_data["Request body data"] = f"Data Files/{unique_name}_body"

            operation_params_only_entry["available_test_data"] = test_data

        operation_params_only_dict[operation] = operation_params_only_entry

    return operation_params_only_dict


def get_required_fields(spec: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Extract required fields from all operations in an OpenAPI specification.

    This function returns only the fields marked as required in each operation.

    Args:
        spec: OpenAPI specification dictionary

    Returns:
        Dictionary mapping operation IDs to their required fields
    """
    operations = extract_operations(spec)
    operation_params_only_dict = {}

    for operation in operations:
        method = operation.split("-")[0]
        object_name = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(spec["paths"][object_name][method])

        operation_params_only_entry = {}

        # parameters
        if "parameters" in obj and obj["parameters"]:
            params = obj["parameters"]
            param_entry = {}

            for param in params:
                if "$ref" in param:
                    param = get_ref(spec, param["$ref"])

                name, dtype, required = None, None, None
                name_parent = find_object_with_key(param, "name")
                type_parent = find_object_with_key(param, "type")
                param_schema_parent = find_object_with_key(param, "$ref")

                required_parent = find_object_with_key(param, "required")
                if name_parent:
                    name = name_parent["name"]
                if type_parent:
                    dtype = type_parent["type"]

                required = False
                if required_parent:
                    required = required_parent["required"]

                if required:
                    if name is not None and param_schema_parent is not None:
                        param_schema = get_ref(spec, param_schema_parent["$ref"])
                        param_entry[name] = get_schema_required_fields(
                            param_schema, spec
                        )
                    elif name is not None and dtype is not None:
                        param_entry[name] = dtype

            operation_params_only_entry["parameters"] = param_entry

        # requestBody
        if "requestBody" in obj:
            schema_obj = find_object_with_key(obj["requestBody"], "schema")
            if schema_obj is not None:
                request_body_schema = schema_obj["schema"]
                operation_params_only_entry["requestBody"] = get_schema_required_fields(
                    request_body_schema, spec
                )
            else:
                operation_params_only_entry["requestBody"] = {}
        else:
            operation_params_only_entry["requestBody"] = None

        operation_params_only_dict[operation] = operation_params_only_entry

    return operation_params_only_dict


def contains_required_parameters(operation: str, origin_spec: Dict[str, Any]) -> bool:
    """
    Check if an operation contains any required parameters.

    Args:
        operation: Operation ID string
        origin_spec: OpenAPI specification dictionary

    Returns:
        True if the operation has any required parameters, False otherwise
    """
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])
    obj = origin_spec["paths"][path][method]
    parameters_obj = find_object_with_key(obj, "parameters")
    if parameters_obj is None:
        return False
    parameters_obj = str(parameters_obj["parameters"])
    return "'required': True" in parameters_obj


def get_relevant_schemas_of_operation(
    operation: str, openapi_spec: Dict[str, Any]
) -> Tuple[List[str], List[str]]:
    """
    Extract schemas relevant to an operation from an OpenAPI specification.

    This function returns both the main response schemas and all related schemas.

    Args:
        operation: Operation ID string
        openapi_spec: OpenAPI specification dictionary

    Returns:
        Tuple of (main_response_schemas, all_relevant_schemas)
    """
    main_response_schemas = []
    relevant_schemas = []
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])

    operation_spec = openapi_spec["paths"][path][method]

    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if isSuccessStatusCode(response_code):
                _, new_relevant_schemas = get_schema_recursive(
                    operation_spec["responses"][response_code], openapi_spec
                )
                if new_relevant_schemas:
                    main_response_schemas.append(new_relevant_schemas[0])
                relevant_schemas.extend(new_relevant_schemas)
    return list(set(main_response_schemas)), list(set(relevant_schemas))


def get_operations_belong_to_schemas(openapi: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Map schemas to operations that use them in an OpenAPI specification.

    This function creates a mapping from schema names to the operations that use them.

    Args:
        openapi: OpenAPI specification dictionary

    Returns:
        Dictionary mapping schema names to lists of operations that use them
    """
    operations_belong_to_schemas = {}

    operations = extract_operations(openapi)
    for operation in operations:
        _, relevant_schemas = get_relevant_schemas_of_operation(operation, openapi)
        for schema in relevant_schemas:
            if schema not in operations_belong_to_schemas:
                operations_belong_to_schemas[schema] = [operation]
            elif operation not in operations_belong_to_schemas[schema]:
                operations_belong_to_schemas[schema].append(operation)
    return operations_belong_to_schemas


def get_test_object_path(api_title: str, operation_id: str, path: str) -> str:
    """
    Generate a path for a test object based on API and operation information.

    Args:
        api_title: Title of the API
        operation_id: Operation ID
        path: API path

    Returns:
        Formatted test object path
    """
    return f"Object Repository/{convert_path_fn(api_title)}/{convert_path_fn(path)}/{operation_id}"


def add_test_object_to_openapi(
    openapi: Dict[str, Any], object_repo_name: str = "API"
) -> Dict[str, Any]:
    """
    Add test object paths to each operation in an OpenAPI specification.

    This function modifies the specification to include test object references.

    Args:
        openapi: OpenAPI specification dictionary
        object_repo_name: Name of the object repository (default: "API")

    Returns:
        Modified OpenAPI specification
    """
    # Find the paths and method and add the new key-value pair of test_object
    for path in openapi["paths"]:
        for method in openapi["paths"][path]:
            if method.lower() not in ["get", "post", "put", "patch", "delete"]:
                continue

            if object_repo_name == "API":
                try:
                    object_repo_name = openapi["info"]["title"]
                except:
                    pass

            try:
                operation_id = openapi["paths"][path][method]["operationId"]
            except:
                operation_id = method.upper()

            openapi["paths"][path][method]["test_object"] = get_test_object_path(
                object_repo_name, operation_id, path
            )
    return openapi


def get_operation_id(openapi_spec: Dict[str, Any], operation: str) -> str:
    """
    Get a unique operation ID for an operation.

    Args:
        openapi_spec: OpenAPI specification dictionary
        operation: Operation ID string

    Returns:
        Unique operation ID string
    """
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])

    operation_spec = openapi_spec["paths"][path][method]

    try:
        operation_id = operation_spec["operationId"]
    except:
        operation_id = method.upper()

    unique_name = f"{convert_path_fn(path)}_{operation_id}"
    return unique_name


def filter_params_has_description(
    operation_param_description: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Filter parameters to include only those with descriptions.

    Args:
        operation_param_description: Dictionary of operation parameters

    Returns:
        Filtered dictionary containing only parameters with descriptions
    """
    filtered_operation_param_description = {}
    for operation in operation_param_description:
        filtered_operation_param_description[operation] = {}
        if (
            "parameters" in operation_param_description[operation]
            and operation_param_description[operation]["parameters"] is not None
        ):
            filtered_operation_param_description[operation]["parameters"] = {}
            for param, value in operation_param_description[operation][
                "parameters"
            ].items():
                if "description" in value:
                    filtered_operation_param_description[operation]["parameters"][
                        param
                    ] = value
        if (
            "requestBody" in operation_param_description[operation]
            and operation_param_description[operation]["requestBody"] is not None
        ):
            filtered_operation_param_description[operation]["requestBody"] = {}
            for param, value in operation_param_description[operation][
                "requestBody"
            ].items():
                if "description" in value:
                    filtered_operation_param_description[operation]["requestBody"][
                        param
                    ] = value
    return filtered_operation_param_description


def get_response_body_name_and_type(
    openapi: Dict[str, Any], operation: str
) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract the name and type of the response body for an operation.

    Args:
        openapi: OpenAPI specification dictionary
        operation: Operation ID string

    Returns:
        Tuple of (schema_name, response_type) or (None, None) if not found
    """
    method = operation.split("-")[0]
    endpoint = "-".join(operation.split("-")[1:])

    operation_spec = openapi["paths"][endpoint][method]
    if "responses" not in operation_spec and "response" not in operation_spec:
        return None, None

    response_spec = None
    if "responses" in operation_spec:
        response_spec = operation_spec["responses"]
    else:
        response_spec = operation_spec["response"]

    success_response = None
    for rk, rv in response_spec.items():
        if isSuccessStatusCode(rk):
            success_response = rv
            break

    if success_response is None:
        return None, None

    response_type = None
    main_response_schema = None

    schema = find_object_with_key(success_response, "schema")
    if schema:
        response_type = schema["schema"].get("type", "object")

    properties = find_object_with_key(success_response, "properties")
    if properties:
        return None, response_type

    main_schema_ref = find_object_with_key(success_response, "$ref")
    if main_schema_ref:
        schema_name = main_schema_ref["$ref"].split("/")[-1]
        return schema_name, response_type

    return None, response_type


def get_relevent_response_schemas_of_operation(
    openapi_spec: Dict[str, Any], operation: str
) -> Tuple[List[str], List[str]]:
    """
    Extract schemas relevant to an operation's responses.

    Args:
        openapi_spec: OpenAPI specification dictionary
        operation: Operation ID string

    Returns:
        Tuple of (main_schemas, all_relevant_schemas)
    """
    main_response_schemas = []
    relevant_schemas = []

    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])

    operation_spec = openapi_spec["paths"][path][method]

    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if isSuccessStatusCode(response_code):
                main_schema_ref = find_object_with_key(
                    operation_spec["responses"][response_code], "$ref"
                )
                if main_schema_ref:
                    main_response_schemas.append(main_schema_ref["$ref"].split("/")[-1])
                    _, new_relevant_schemas = get_schema_recursive(
                        operation_spec["responses"][response_code], openapi_spec
                    )
                    relevant_schemas.extend(new_relevant_schemas)
    return main_response_schemas, list(set(relevant_schemas))


def get_main_response_schemas_of_operation(
    openapi_spec: Dict[str, Any], operation: str
) -> List[str]:
    """
    Extract the main response schemas for an operation.

    Args:
        openapi_spec: OpenAPI specification dictionary
        operation: Operation ID string

    Returns:
        List of main response schema names
    """
    main_response_schemas = []

    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])

    operation_spec = openapi_spec["paths"][path][method]

    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if isSuccessStatusCode(response_code):
                main_schema_ref = find_object_with_key(
                    operation_spec["responses"][response_code], "$ref"
                )
                if main_schema_ref:
                    main_response_schemas.append(main_schema_ref["$ref"].split("/")[-1])
    return main_response_schemas


def get_relevant_schema_of_operation(
    operation: str, openapi_spec: Dict[str, Any]
) -> List[str]:
    """
    Extract all schemas relevant to an operation.

    Args:
        operation: Operation ID string
        openapi_spec: OpenAPI specification dictionary

    Returns:
        List of relevant schema names
    """
    relevant_schemas = []
    method = operation.split("-")[0]
    path = "-".join(operation.split("-")[1:])

    operation_spec = openapi_spec["paths"][path][method]

    if "responses" in operation_spec:
        for response_code in operation_spec["responses"]:
            if isSuccessStatusCode(response_code):
                _, new_relevant_schemas = get_schema_recursive(
                    operation_spec["responses"][response_code], openapi_spec
                )
                relevant_schemas.extend(new_relevant_schemas)
    return list(set(relevant_schemas))


def simplify_openapi(openapi: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Create a simplified version of an OpenAPI specification.

    This function extracts the essential information from an OpenAPI specification
    and returns a simplified structure.

    Args:
        openapi: OpenAPI specification dictionary

    Returns:
        Simplified OpenAPI specification
    """
    operations = extract_operations(openapi)
    simple_openapi = {}

    for operation in operations:
        method = operation.split("-")[0]
        path = "-".join(operation.split("-")[1:])
        obj = copy.deepcopy(openapi["paths"][path][method])

        simple_operation_spec = {}

        if "summary" in obj:
            simple_operation_spec["summary"] = obj["summary"]

        # parameters
        if "parameters" in obj and obj["parameters"]:
            params = obj["parameters"]
            param_entry = {}

            for param in params:
                if "$ref" in param:
                    param = get_ref(openapi, param["$ref"])

                # get description string
                description_string = ""
                description_parent = find_object_with_key(param, "description")
                if description_parent and not isinstance(
                    description_parent["description"], dict
                ):
                    description_string = (
                        " (description: "
                        + description_parent["description"].strip(" .")
                        + ")"
                    )

                name, dtype = None, None
                name_parent = find_object_with_key(param, "name")
                type_parent = find_object_with_key(param, "type")
                param_schema_parent = find_object_with_key(param, "$ref")

                if name_parent:
                    name = name_parent["name"]
                if type_parent:
                    dtype = type_parent["type"]

                if name is not None and param_schema_parent is not None:
                    param_schema = get_ref(openapi, param_schema_parent["$ref"])
                    param_entry[name] = get_schema_params(param_schema, openapi)
                elif name is not None and dtype is not None:
                    param_entry[name] = dtype + description_string

            if param_entry:
                simple_operation_spec["parameters"] = param_entry

        # requestBody
        if "requestBody" in obj:
            body_entry = {}

            schema_obj = find_object_with_key(obj["requestBody"], "schema")
            if schema_obj is not None:
                request_body_schema = schema_obj["schema"]
                body_entry = get_schema_params(
                    request_body_schema, openapi, get_description=True
                )

            if body_entry:
                simple_operation_spec["requestBody"] = body_entry

        # responseBody (single response body)
        if "responses" in obj or "response" in obj:
            response_entry = {}

            if method.lower() != "delete":
                if "responses" in obj:
                    responses = obj["responses"]
                else:
                    responses = obj["response"]

                success_response = None

                for rk, rv in responses.items():
                    if isSuccessStatusCode(rk):
                        success_response = rv
                        break

                if success_response is not None:
                    response_entry = get_schema_params(
                        success_response, openapi, get_description=True
                    )

                if response_entry:
                    simple_operation_spec["responseBody"] = response_entry

        simple_openapi[operation] = simple_operation_spec

    return simple_openapi
