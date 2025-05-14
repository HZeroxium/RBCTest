# /src/execute_code_in_excel.py

"""
Excel Code Execution Module

This module provides functionality to execute verification code stored in Excel files
and update the results in the same files.
"""

import os
import uuid
import pandas as pd
from datetime import datetime
from typing import Optional

from utils.execution_utils import (
    execute_response_constraint_verification_script,
    execute_request_parameter_constraint_verification_script,
    get_api_responses,
    get_request_informations,
    get_request_bodies,
    fix_json,
)

from models.execution_models import ExecutionConfig, ExecutionStats


def re_execute_code(
    code_excel: str, is_req_res: bool = False, dataset_folder: Optional[str] = None
) -> ExecutionStats:
    """
    Execute verification code stored in an Excel file and update the results.

    Args:
        code_excel: Path to the Excel file containing verification code
        is_req_res: Whether this is a request-response constraint file
        dataset_folder: Path to the dataset folder containing API responses

    Returns:
        Statistics of the execution results
    """
    # Create configuration
    config = ExecutionConfig(
        excel_path=code_excel,
        is_request_response=is_req_res,
        dataset_folder=dataset_folder,
    )

    # Initialize statistics
    stats = ExecutionStats()

    # Load the Excel file
    df = pd.read_excel(code_excel)
    df = df.fillna("")

    # Process each row in the Excel file
    for index, row in df.iterrows():
        # Initialize response and request files
        request_informations = []
        api_responses = []
        request_bodies = []

        # Determine the operation to use
        if "attribute inferred from operation" in df.columns:
            operation_col = "attribute inferred from operation"
            df_filter_operation = df[df[operation_col] == row[operation_col]]
            operation = row[operation_col]
        else:
            operation_col = "operation"
            df_filter_operation = df[df[operation_col] == row[operation_col]]
            operation = row[operation_col]

        # Process response bodies
        response_bodies = (
            df_filter_operation["API response"].tolist()
            if "API response" in df_filter_operation.columns
            else []
        )
        for i, response_body in enumerate(response_bodies):
            # Handle invalid response bodies
            if (
                response_body == ""
                or response_body == "nan"
                or not isinstance(response_body, str)
            ):
                response_body = "{}"

            # Create and save the response file
            response_dir = os.path.abspath(
                os.path.join(dataset_folder, operation, "responseBody")
            )
            os.makedirs(response_dir, exist_ok=True)
            file_path = os.path.join(response_dir, f"{i}.json").replace("\\", "/")

            with open(file_path, "w") as f:
                f.write(response_body)

            api_responses.append(file_path)

        # Process request information if this is a request-response constraint
        if is_req_res:
            # Process query parameters
            if "request information" in df_filter_operation.columns:
                request_information = df_filter_operation[
                    "request information"
                ].tolist()
                for i, request_info in enumerate(request_information):
                    # Handle invalid request info
                    if (
                        request_info == ""
                        or request_info == "nan"
                        or not isinstance(request_info, str)
                    ):
                        request_info = "{}"

                    # Create and save the request parameters file
                    query_dir = os.path.abspath(
                        os.path.join(dataset_folder, operation, "queryParameters")
                    )
                    os.makedirs(query_dir, exist_ok=True)
                    file_path = os.path.join(query_dir, f"{i}.json").replace("\\", "/")

                    with open(file_path, "w") as f:
                        f.write(request_info)

                    request_informations.append(file_path)

                # Process request bodies
                request_body = df_filter_operation["request information"].tolist()
                for i, request in enumerate(request_body):
                    # Handle invalid request bodies
                    if (
                        request == ""
                        or request == "nan"
                        or not isinstance(request, str)
                    ):
                        request = "{}"

                    # Create and save the request body file
                    body_dir = os.path.abspath(
                        os.path.join(dataset_folder, operation, "bodyParameters")
                    )
                    os.makedirs(body_dir, exist_ok=True)
                    file_path = os.path.join(body_dir, f"{i}.json").replace("\\", "/")

                    with open(file_path, "w") as f:
                        f.write(request)

                    request_bodies.append(file_path)
        else:
            # Create empty request files for response-property constraints
            request_informations = request_bodies = ["{}"] * len(api_responses)

        # Get the verification code
        code = row["verification script"]

        # Initialize tracking variables
        execution_statuses = []
        satisfied = 0
        mismatched = 0
        unknown = 0
        code_error = 0
        mismatches_json = []

        # Execute the verification code for each API response
        for i, (api_response, request_information, request_body) in enumerate(
            zip(api_responses, request_informations, request_bodies)
        ):
            if not is_req_res:
                # Execute response property constraint verification
                executable_script, new_execution_status = (
                    execute_response_constraint_verification_script(code, api_response)
                )
            else:
                # Execute request-response constraint verification
                part = row["part"]
                parameter = row["corresponding attribute"]
                field_name = row["attribute"]

                if part == "parameters":
                    # Use query parameters
                    executable_script, new_execution_status = (
                        execute_request_parameter_constraint_verification_script(
                            code,
                            api_response,
                            request_information,
                            parameter,
                            field_name,
                        )
                    )
                else:
                    # Use request body
                    executable_script, new_execution_status = (
                        execute_request_parameter_constraint_verification_script(
                            code, api_response, request_body, parameter, field_name
                        )
                    )

            # Track status
            execution_statuses.append(new_execution_status)

            # Update counts based on status
            if new_execution_status == "satisfied":
                satisfied += 1
            elif new_execution_status == "mismatched":
                mismatched += 1
                mismatches_json.append(api_response)

                # Save mismatched code for debugging
                mismatched_code_folder = os.path.join("code", "mismatched")
                os.makedirs(mismatched_code_folder, exist_ok=True)
                with open(
                    os.path.join(mismatched_code_folder, f"{uuid.uuid4()}.py"), "w"
                ) as f:
                    f.write(executable_script)
            elif new_execution_status == "code error":
                code_error += 1

                # Save error code for debugging
                code_error_folder = os.path.join("code", "code_error")
                os.makedirs(code_error_folder, exist_ok=True)
                with open(
                    os.path.join(code_error_folder, f"{uuid.uuid4()}.py"), "w"
                ) as f:
                    f.write(executable_script)
            else:
                unknown += 1

        # Update execution results in the dataframe
        df.at[index, "satisfied"] = bool(satisfied > 0)
        df.at[index, "mismatched"] = bool(mismatched > 0)
        df.at[index, "unknown"] = bool(not (satisfied > 0 or mismatched > 0))
        df.at[index, "code error"] = code_error

        # Save the executed code for reference
        with open(f"code/{index}.py", "w") as f:
            f.write(executable_script)

        # Update statistics
        stats.satisfied_count += satisfied
        stats.mismatched_count += mismatched
        stats.unknown_count += unknown
        stats.code_error_count += code_error
        stats.total_count += 1

    # Save the updated Excel file
    df.to_excel(code_excel, index=False)

    print(f"Re-executed {stats.total_count} code snippets")
    return stats


def main():
    """Main function to run the code execution."""
    # Create code directory if it doesn't exist
    if not os.path.exists("code"):
        os.makedirs("code")

    # Configuration
    approach_folder = "approaches/rbctest_our_data"
    api_names = ["GitLab Repository"]

    # Process each API
    for api_name in api_names:
        dataset_folder = f"RBCTest_dataset/{api_name}"

        # Skip if dataset doesn't exist
        if not os.path.exists(dataset_folder):
            print(f"{dataset_folder} does not exist")
            continue

        # Process request-response constraints
        rr_file = f"{approach_folder}/{api_name} API/request_response_constraints.xlsx"
        if os.path.exists(rr_file):
            print(f"Executing codes in {rr_file}")
            re_execute_code(rr_file, is_req_res=True, dataset_folder=dataset_folder)
        else:
            print(f"{rr_file} does not exist")

        # Process response property constraints
        rp_file = f"{approach_folder}/{api_name} API/response_property_constraints.xlsx"
        if os.path.exists(rp_file):
            print(f"Executing codes in {rp_file}")
            re_execute_code(rp_file, dataset_folder=dataset_folder)
        else:
            print(f"{rp_file} does not exist")


if __name__ == "__main__":
    main()
