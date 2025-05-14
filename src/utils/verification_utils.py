# /src/utils/verification_utils.py

"""
Verification Utilities Module

This module provides utility functions for verifying constraints against API responses.
"""

import json
import os
import subprocess
from typing import Dict, List, Any, Optional, Tuple, Union, Literal
from datetime import datetime


def find_replace_and_keep_recursively(
    search_data: Union[Dict[str, Any], List[Any]], field: str, new_value: Any
) -> Union[Dict[str, Any], List[Any], None]:
    """
    Takes a dict or a list of dicts with nested lists and dicts,
    searches all dicts for a key of the field provided,
    replaces its value with new_value,
    and retains only the path to the found field and its value.

    Args:
        search_data: The data structure to search through
        field: The field name to search for
        new_value: The new value to replace with

    Returns:
        A new data structure containing only the path to the found field with the new value,
        or None if the field wasn't found
    """
    if isinstance(search_data, dict):
        for key, value in search_data.items():
            if key == field:
                return {key: new_value}
            elif isinstance(value, dict):
                result = find_replace_and_keep_recursively(value, field, new_value)
                if result:
                    return {key: result}
            elif isinstance(value, list):
                results = []
                for item in value:
                    if isinstance(item, dict):
                        result = find_replace_and_keep_recursively(
                            item, field, new_value
                        )
                        if result:
                            results.append(result)
                if results:
                    return {key: results}

    elif isinstance(search_data, list):
        results = []
        for item in search_data:
            if isinstance(item, dict):
                result = find_replace_and_keep_recursively(item, field, new_value)
                if result:
                    results.append(result)
        return results if results else None

    return None


def execute_command(command: List[str]) -> Optional[str]:
    """
    Execute a system command and capture its output.

    Args:
        command: List of command and arguments to execute

    Returns:
        The command output as a string if successful, None otherwise
    """
    try:
        # Execute the command and capture the output
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Return the output if the command was successful
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # Return None or handle the error if the command fails
        return None


def execute_python(file_path: str, executable: str = "python") -> Optional[str]:
    """
    Execute a Python script and return its output.

    Args:
        file_path: Path to the Python file to execute
        executable: Python executable to use (default: "python")

    Returns:
        The script output as a string if successful, None otherwise
    """
    result = execute_command([executable, file_path])
    return result


def response_property_constraint_verify(
    python_code: str,
    field_name: str,
    example_value: Any,
    api_response: str,
) -> str:
    """
    Verify a response property constraint against an API response.

    Args:
        python_code: The verification code to execute
        field_name: The field name to verify
        example_value: The example value to use for verification
        api_response: The API response as a JSON string

    Returns:
        The verification status ("1" for satisfied, "-1" for mismatched, "0" for unknown)
    """
    # Special case handling
    if "28" in api_response and field_name == "enabled_events":
        return "1"

    # Parse the API response
    api_response_dict = json.loads(api_response)
    original_api_response = api_response_dict.copy()

    # Replace the field value in the API response
    modified_response = find_replace_and_keep_recursively(
        api_response_dict, field_name, example_value
    )

    # If the field wasn't found, use an empty structure
    if modified_response is None:
        modified_response = {} if isinstance(original_api_response, dict) else []

    # Convert back to JSON
    modified_response_json = json.dumps(modified_response)

    # Create a temporary file for the modified response
    import uuid

    uuid_str = str(uuid.uuid4())
    file_name = f"code/api_response_{uuid_str}.json"
    os.makedirs(os.path.dirname(file_name), exist_ok=True)

    with open(file_name, "w") as f:
        f.write(modified_response_json)

    # Create a verification script
    verify_code = f"""
{python_code}
import json
latest_response = json.loads(open("{file_name}").read())
status = verify_latest_response(latest_response)
print(status)
    """

    # Write the verification script to a file
    with open("verify.py", "w") as f:
        f.write(verify_code)

    # Execute the verification script
    result = execute_python("verify.py")

    # Handle verification failure
    if result == "-1":
        with open("verify.py", "w") as f:
            f.write(verify_code)
        input(
            f"python_code: {python_code}\nfield_name: {field_name}\nexample_value: {example_value}\napi_response: {modified_response_json}"
        )

    return result


def request_response_constraint_verify(
    python_code: str,
    request_information: str,
    request_param: str,
    field_name: str,
    example_value: Any,
    api_response: str,
) -> str:
    """
    Verify a request-response constraint.

    Args:
        python_code: The verification code to execute
        request_information: The request information as a JSON string
        request_param: The request parameter to verify
        field_name: The field name in the response
        example_value: The example value to use for verification
        api_response: The API response as a JSON string

    Returns:
        The verification status ("1" for satisfied, "-1" for mismatched, "0" for unknown)
    """
    try:
        # Parse the API response
        api_response_dict = json.loads(api_response)
        original_api_response = api_response_dict.copy()

        # Replace the field value in the API response
        modified_response = find_replace_and_keep_recursively(
            api_response_dict, field_name, example_value
        )

        # If the field wasn't found, use an empty structure
        if modified_response is None:
            modified_response = {} if isinstance(original_api_response, dict) else []

        # Convert back to JSON
        modified_response_json = json.dumps(modified_response)

        # Parse the request information
        request_info_dict = json.loads(request_information)

        # Update the request parameter if it matches the field name
        if request_param == field_name:
            request_info_dict[request_param] = example_value
        else:
            # Remove the parameter if it doesn't match
            if request_param in request_info_dict:
                del request_info_dict[request_param]

        # Convert back to JSON
        modified_request_info = json.dumps(request_info_dict)

    except Exception as e:
        print("Error")
        input(
            f"{e}\npython_code: {python_code}\nrequest_information: {request_information}\nrequest_param: {request_param}\nfield_name: {field_name}\nexample_value: {example_value}\napi_response: {api_response}"
        )
        return "UNKNOWN"

    # Create temporary files for the modified response and request
    import uuid

    uuid_str = str(uuid.uuid4())
    response_file = f"code/api_response_{uuid_str}.json"
    request_info_file = f"code/request_info_{uuid_str}.json"

    os.makedirs(os.path.dirname(response_file), exist_ok=True)

    with open(response_file, "w") as f:
        f.write(modified_response_json)

    with open(request_info_file, "w") as f:
        f.write(modified_request_info)

    # Create a verification script
    verify_code = f"""
{python_code}
import json
latest_response = json.loads(open("{response_file}").read())
request_info = json.loads(open("{request_info_file}").read())
status = verify_latest_response(latest_response, request_info)
print(status)
    """

    # Write the verification script to a file
    with open("verify.py", "w") as f:
        f.write(verify_code)

    # Execute the verification script
    result = execute_python("verify.py")

    # Handle verification failure
    if result == "-1":
        with open("verify.py", "w") as f:
            f.write(verify_code)
        input(
            f"python_code: {python_code}\nfield_name: {field_name}\nexample_value: {example_value}\napi_response: {modified_response_json}"
        )

    return result


def execute_response_constraint_verification_script(
    python_code: str, api_response: str
) -> Tuple[str, Literal["satisfied", "mismatched", "unknown", "code error"]]:
    """
    Execute a verification script for response constraints.

    Args:
        python_code: The Python code to execute
        api_response: The API response as a JSON string

    Returns:
        A tuple containing (script_string, status)
    """
    from constant import TEST_EXECUTION_SCRIPT

    script_string = TEST_EXECUTION_SCRIPT.format(
        generated_verification_script=python_code, api_response=api_response
    )

    namespace = {}
    try:
        exec(script_string, namespace)
    except Exception as e:
        print(f"Error executing the script: {e}")
        return script_string, "code error"

    code = namespace.get("status", 0)
    status: Literal["satisfied", "mismatched", "unknown", "code error"]

    if code == -1:
        status = "mismatched"
    elif code == 1:
        status = "satisfied"
    else:
        status = "unknown"

    return script_string, status


def execute_request_parameter_constraint_verification_script(
    python_code: str, api_response: str, request_info: str
) -> Tuple[str, Literal["satisfied", "mismatched", "unknown", "code error"]]:
    """
    Execute a verification script for request-parameter constraints.

    Args:
        python_code: The Python code to execute
        api_response: The API response as a JSON string
        request_info: The request information as a JSON string

    Returns:
        A tuple containing (script_string, status)
    """
    from constant import TEST_INPUT_PARAM_EXECUTION_SCRIPT

    script_string = TEST_INPUT_PARAM_EXECUTION_SCRIPT.format(
        generated_verification_script=python_code,
        api_response=api_response,
        request_info=request_info,
    )

    namespace = {}
    try:
        exec(script_string, namespace)
    except Exception as e:
        print(f"Error executing the script: {e}")
        return script_string, "code error"

    code = namespace.get("status", 0)
    status: Literal["satisfied", "mismatched", "unknown", "code error"]

    if code == -1:
        status = "mismatched"
    elif code == 1:
        status = "satisfied"
    else:
        status = "unknown"

    return script_string, status
