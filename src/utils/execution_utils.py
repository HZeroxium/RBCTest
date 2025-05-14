"""
Execution Utilities Module

This module provides utility functions for executing verification code.
"""

import os
import json
from typing import Tuple, Dict, List, Any, Optional
from datetime import datetime


def execute_request_parameter_constraint_verification_script(
    python_code: str,
    api_response: str,
    request_info: str,
    request_param: str,
    field_name: str,
) -> Tuple[str, str]:
    """
    Execute a verification script for request-parameter constraints.

    Args:
        python_code: The Python code to execute
        api_response: The API response as a JSON string
        request_info: The request information as a JSON string
        request_param: The request parameter to verify
        field_name: The field name in the response

    Returns:
        A tuple containing (script_string, status)
    """
    from constant import INPUT_PARAM_EXECUTION_SCRIPT

    script_string = INPUT_PARAM_EXECUTION_SCRIPT.format(
        generated_verification_script=python_code,
        api_response=api_response,
        request_info=request_info,
        request_param=request_param,
        field_name=field_name,
    )

    namespace = {}
    try:
        exec(script_string, namespace)
    except Exception as e:
        print(f"Error executing the script: {e}")
        return script_string, "code error"

    code = namespace.get("status", 0)
    status = ""

    if code == -1:
        status = "mismatched"
        error_codes_folder = "error_codes"
        os.makedirs(error_codes_folder, exist_ok=True)
        file_name = f"{datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f')}.py"
        with open(os.path.join(error_codes_folder, file_name), "w") as f:
            f.write(script_string)
    elif code == 1:
        status = "satisfied"
    else:
        status = "unknown"

    return script_string, status


def execute_response_constraint_verification_script(
    python_code: str, file_path: str
) -> Tuple[str, str]:
    """
    Execute a verification script for response constraints.

    Args:
        python_code: The Python code to execute
        file_path: Path to the API response file

    Returns:
        A tuple containing (script_string, status)
    """
    from constant import EXECUTION_SCRIPT

    script_string = EXECUTION_SCRIPT.format(
        generated_verification_script=python_code, file_path=file_path
    )

    namespace = {}
    try:
        exec(script_string, namespace)
    except Exception as e:
        print(f"Error executing the script: {e}")
        return script_string, "code error"

    code = namespace.get("status", 0)
    status = ""

    if code == -1:
        status = "mismatched"
    elif code == 1:
        status = "satisfied"
    else:
        status = "unknown"

    return script_string, status


def fix_json(json_str: str) -> str:
    """
    Clean up a JSON string by removing comments.

    Args:
        json_str: The JSON string to fix

    Returns:
        The fixed JSON string
    """
    lines = json_str.split("\n")
    new_lines = []

    for line in lines:
        if "//" in line:
            # If // is in the line and not inside double quotes, delete from // to the end
            new_line = ""
            inside_double_quote = False

            for i in range(len(line)):
                if line[i] == '"':
                    inside_double_quote = not inside_double_quote

                if not inside_double_quote and line[i : i + 2] == "//":
                    break

                new_line += line[i]

            line = new_line

        new_lines.append(line)

    return "\n".join(new_lines)


def get_request_informations(dataset_folder: str) -> List[str]:
    """
    Get all request information files from a dataset folder.

    Args:
        dataset_folder: Path to the dataset folder

    Returns:
        List of paths to request information files
    """
    request_informations = []
    query_params_path = os.path.join(dataset_folder, "queryParameters")

    if os.path.exists(query_params_path):
        for file in os.listdir(query_params_path):
            request_informations.append(
                os.path.join(dataset_folder, "queryParameters", file).replace("\\", "/")
            )

    return request_informations


def get_api_responses(dataset_folder: str) -> List[str]:
    """
    Get all API response files from a dataset folder.

    Args:
        dataset_folder: Path to the dataset folder

    Returns:
        List of paths to API response files
    """
    api_responses = []
    response_body_path = os.path.join(dataset_folder, "responseBody")

    if os.path.exists(response_body_path):
        for file in os.listdir(response_body_path):
            api_responses.append(
                os.path.join(dataset_folder, "responseBody", file).replace("\\", "/")
            )

    return api_responses


def get_request_bodies(dataset_folder: str) -> List[str]:
    """
    Get all request body files from a dataset folder.

    Args:
        dataset_folder: Path to the dataset folder

    Returns:
        List of paths to request body files
    """
    request_bodies = []
    body_params_path = os.path.join(dataset_folder, "bodyParameters")

    if os.path.exists(body_params_path):
        for file in os.listdir(body_params_path):
            request_bodies.append(
                os.path.join(dataset_folder, "bodyParameters", file).replace("\\", "/")
            )

    return request_bodies
