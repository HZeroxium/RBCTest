# /src/constraints_test_generation.py

"""
Constraints Test Generation Module

This module handles the generation of verification scripts for API constraints,
both for response property constraints and request-response constraints.
"""

import os
import json
import dotenv
import pandas as pd
import yaml
import openai
from pathlib import Path
from typing import Dict, List, Optional, Literal, Any, Union, Tuple, Set

from utils.openapi_utils import (
    load_openapi,
    simplify_openapi,
    get_simplified_schema,
    get_response_body_name_and_type,
)
from utils.llm_utils import llm_chat_completion
from utils.dict_utils import filter_dict_by_key
from utils.text_extraction import extract_python_code


from models.verification_script_models import (
    VerificationScriptConfig,
    ConstraintInfo,
    RequestResponseConstraintInfo,
    VerificationScriptResult,
    ResponsePropertyVerificationResult,
    RequestResponseVerificationResult,
)

from constant import (
    CONST_INSIDE_RESPONSEBODY_SCRIPT_GEN_PROMPT,
    CONST_RESPONSEBODY_PARAM_SCRIPT_GEN_PROMPT,
    TEST_EXECUTION_SCRIPT,
    TEST_INPUT_PARAM_EXECUTION_SCRIPT,
)

# Load environment variables and API keys
dotenv.load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY")


def export_file(content: str, directory: str, filename: str) -> None:
    """
    Export content to a file, creating directories if needed

    Args:
        content: Content to write to file
        directory: Directory path to save the file in
        filename: Name of the file to create
    """
    os.makedirs(directory, exist_ok=True)
    file_path = Path(directory) / filename

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(content)


class VerificationScriptGenerator:
    """
    Generator for API constraint verification scripts.

    This class handles the generation of verification scripts for both
    response property constraints and request-response constraints.
    """

    def __init__(
        self,
        service_name: str,
        experiment_dir: str,
        request_response_constraints_file: Optional[str] = None,
        response_property_constraints_file: Optional[str] = None,
    ):
        """
        Initialize the verification script generator.

        Args:
            service_name: Name of the service to generate verification scripts for
            experiment_dir: Directory to store experiment outputs
            request_response_constraints_file: Path to file with request-response constraints
            response_property_constraints_file: Path to file with response property constraints
        """
        # Load OpenAPI specification
        self.openapi_spec = load_openapi(f"RBCTest_dataset/{service_name}/openapi.json")
        self.simplified_openapi = simplify_openapi(self.openapi_spec)
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)

        # Setup experiment directory
        self.experiment_dir = experiment_dir
        os.makedirs(self.experiment_dir, exist_ok=True)

        # Save simplified OpenAPI for debugging
        with open("simplified_openapi.json", "w") as file:
            json.dump(self.simplified_openapi, file, indent=2)

        # Service information
        self.service_name = service_name
        self.api_title = self.openapi_spec["info"]["title"]
        self.experiment_dir = f"{experiment_dir}/{self.api_title}"
        os.makedirs(self.experiment_dir, exist_ok=True)

        # Store generated verification scripts
        self.generated_verification_scripts: List[
            Union[ResponsePropertyVerificationResult, RequestResponseVerificationResult]
        ] = []

        # Process constraint files if provided
        if request_response_constraints_file:
            self._process_request_response_constraints(
                request_response_constraints_file
            )

        if response_property_constraints_file:
            self._process_response_property_constraints(
                response_property_constraints_file
            )

    def _process_request_response_constraints(self, file_path: str) -> None:
        """
        Process request-response constraints from an Excel file.

        Args:
            file_path: Path to the Excel file containing request-response constraints
        """
        self.request_response_constraints_file = file_path
        self.request_response_constraints_df = pd.read_excel(
            file_path, sheet_name="Sheet1"
        )
        self.request_response_constraints_df = (
            self.request_response_constraints_df.fillna("")
        )
        self.verify_request_parameter_constraints()

    def _process_response_property_constraints(self, file_path: str) -> None:
        """
        Process response property constraints from an Excel file.

        Args:
            file_path: Path to the Excel file containing response property constraints
        """
        self.response_property_constraints_file = file_path
        self.response_property_constraints_df = pd.read_excel(
            file_path, sheet_name="Sheet1"
        )
        self.response_property_constraints_df = (
            self.response_property_constraints_df.fillna("")
        )
        self.verify_inside_response_body_constraints()

    def track_generated_script(
        self, generating_script: Dict[str, str]
    ) -> Optional[
        Union[ResponsePropertyVerificationResult, RequestResponseVerificationResult]
    ]:
        """
        Check if a script with the same parameters has already been generated.

        Args:
            generating_script: Dictionary with script parameters

        Returns:
            The previously generated script result if found, None otherwise
        """
        for generated_script in self.generated_verification_scripts:
            if (
                generated_script.response_resource
                == generating_script["response_resource"]
                and generated_script.attribute == generating_script["attribute"]
                and generated_script.description == generating_script["description"]
                and generated_script.operation == generating_script["operation"]
            ):
                return generated_script
        return None

    def track_generated_request_parameter_script(
        self, generating_script: Dict[str, str]
    ) -> Optional[RequestResponseVerificationResult]:
        """
        Check if a request parameter script with the same parameters has already been generated.

        Args:
            generating_script: Dictionary with script parameters

        Returns:
            The previously generated request parameter script result if found, None otherwise
        """
        for generated_script in self.generated_verification_scripts:
            # Skip non-RequestResponseVerificationResult entries
            if not isinstance(generated_script, RequestResponseVerificationResult):
                continue

            require_keys = [
                "response_resource",
                "attribute",
                "description",
                "corresponding_operation",
                "corresponding_attribute",
                "corresponding_description",
                "operation",
            ]

            match = True
            for key in require_keys:
                if getattr(generated_script, key) != generating_script[key]:
                    match = False
                    break

            if match:
                return generated_script

        return None

    def verify_inside_response_body_constraints(self) -> None:
        """
        Verify constraints inside response bodies.

        This method processes each constraint in the response property constraints dataframe,
        generates a verification script for it, and updates the dataframe with the results.
        """
        if not hasattr(self, "response_property_constraints_df"):
            print("No response property constraints dataframe found.")
            return

        df_length = len(self.response_property_constraints_df)
        verification_scripts = [""] * df_length
        executable_scripts = [""] * df_length
        statuses = [""] * df_length
        confirmations = [""] * df_length
        revised_scripts = [""] * df_length
        revised_executable_scripts = [""] * df_length
        revised_script_statuses = [""] * df_length

        for index, row in self.response_property_constraints_df.iterrows():
            response_resource = row["response resource"]
            attribute = row["attribute"]
            description = row["description"]
            operation = row["operation"]

            print(
                f"Generating verification script for {response_resource} - {attribute} - {description}"
            )

            # Create script tracking information
            generating_script = {
                "operation": operation,
                "response_resource": response_resource,
                "attribute": attribute,
                "description": description,
                "verification_script": "",
                "executable_script": "",
                "status": "",
                "confirmation": "",
                "revised_script": "",
                "revised_executable_script": "",
                "revised_status": "",
            }

            # Check if we've already generated this script
            generated_script = self.track_generated_script(generating_script)
            if generated_script:
                verification_scripts[index] = generated_script.verification_script
                executable_scripts[index] = generated_script.executable_script
                statuses[index] = generated_script.status
                confirmations[index] = generated_script.confirmation
                revised_scripts[index] = generated_script.revised_script
                revised_executable_scripts[index] = (
                    generated_script.revised_executable_script
                )
                revised_script_statuses[index] = generated_script.revised_status
                continue

            # Get response specification information
            response_specification = self.simplified_openapi[operation].get(
                "responseBody", {}
            )
            response_specification = filter_dict_by_key(
                response_specification, attribute
            )

            # Get response schema structure
            main_response_schema_name, response_type = get_response_body_name_and_type(
                self.openapi_spec, operation
            )
            print(f"Main response schema name: {main_response_schema_name}")
            print(f"Response type: {response_type}")

            if not main_response_schema_name:
                response_schema_structure = response_type
            else:
                if response_type == "object":
                    response_schema_structure = f"{main_response_schema_name} object"
                else:
                    response_schema_structure = (
                        f"array of {main_response_schema_name} objects"
                    )

            # Prepare response schema specification
            response_schema_specification = ""
            if main_response_schema_name:
                response_schema_specification = (
                    f"- Data structure of the response body: {response_schema_structure}\n"
                    f"- Specification of {main_response_schema_name} object: {json.dumps(response_specification)}"
                )
            else:
                response_schema_specification = (
                    f"- Data structure of the response body: {response_schema_structure}\n"
                    f"- Specification: {json.dumps(response_specification)}"
                )

            # Extract additional attribute specifications
            attribute_spec = self.simplified_schemas.get(response_resource, {}).get(
                attribute, ""
            )
            other_description = ""

            attribute_spec = (
                self.openapi_spec.get("components", {})
                .get("schemas", {})
                .get(response_resource, {})
                .get("properties", {})
                .get(attribute, "")
            )

            if not attribute_spec:
                attribute_spec = (
                    self.openapi_spec.get("definitions", {})
                    .get(response_resource, {})
                    .get("properties", {})
                    .get(attribute, "")
                )

            if attribute_spec:
                other_description = json.dumps(attribute_spec)

            # Generate verification script
            python_verification_script_generation_prompt = (
                CONST_INSIDE_RESPONSEBODY_SCRIPT_GEN_PROMPT.format(
                    attribute=attribute,
                    description=other_description if other_description else description,
                    response_schema_specification=response_schema_specification,
                )
            )

            print(python_verification_script_generation_prompt)

            # Log the prompt for reference
            os.makedirs(self.experiment_dir, exist_ok=True)
            with open(f"{self.experiment_dir}/prompts.txt", "a") as file:
                file.write(
                    f"Prompt for constraint {index}:\n{python_verification_script_generation_prompt}\n"
                )

            # Call LLM to generate the verification script
            python_verification_script_response = llm_chat_completion(
                python_verification_script_generation_prompt, model="gpt-4-turbo"
            )

            print(f"Generated script: {python_verification_script_response}")

            # Extract the Python code from the response
            python_verification_script = extract_python_code(
                python_verification_script_response
            )

            # In the original code, script execution is commented out
            # script_string, status = execute_response_constraint_verification_script(python_verification_script, row['API response'])
            script_string = ""
            status = "unknown"

            # Update the arrays with results
            verification_scripts[index] = python_verification_script
            executable_scripts[index] = script_string
            statuses[index] = status

            # Create a result object and add to tracking
            result = ResponsePropertyVerificationResult(
                operation=operation,
                response_resource=response_resource,
                attribute=attribute,
                description=description,
                verification_script=python_verification_script,
                executable_script=script_string,
                status=status,
                confirmation="",
                revised_script="",
                revised_executable_script="",
                revised_status="",
            )

            self.generated_verification_scripts.append(result)

            # Update the dataframe with new values
            self.response_property_constraints_df["verification script"] = pd.array(
                verification_scripts
            )
            self.response_property_constraints_df["status"] = pd.array(statuses)
            self.response_property_constraints_df["script confirmation"] = pd.array(
                confirmations
            )
            self.response_property_constraints_df["revised script"] = pd.array(
                revised_scripts
            )
            self.response_property_constraints_df["revised executable script"] = (
                pd.array(revised_executable_scripts)
            )
            self.response_property_constraints_df["revised status"] = pd.array(
                revised_script_statuses
            )

            # Save the dataframe after each iteration
            self.response_property_constraints_df.to_excel(
                self.response_property_constraints_file,
                sheet_name="Sheet1",
                index=False,
            )

    def verify_request_parameter_constraints(self) -> None:
        """
        Verify request parameter constraints.

        This method processes each constraint in the request-response constraints dataframe,
        generates a verification script for it, and updates the dataframe with the results.
        """
        if not hasattr(self, "request_response_constraints_df"):
            print("No request response constraints dataframe found.")
            return

        df_length = len(self.request_response_constraints_df)
        verification_scripts = [""] * df_length
        executable_scripts = [""] * df_length
        statuses = [""] * df_length
        confirmations = [""] * df_length
        revised_scripts = [""] * df_length
        revised_executable_scripts = [""] * df_length
        revised_script_statuses = [""] * df_length

        for index, row in self.request_response_constraints_df.iterrows():
            response_resource = row["response resource"]
            attribute = row["attribute"]
            description = str(row["description"])
            corresponding_operation = (row["attribute inferred from operation"],)
            corresponding_part = row["part"]
            corresponding_attribute = row["corresponding attribute"]
            corresponding_description = row["corresponding attribute description"]

            # Check if the constraint should be processed
            constraint_correctness = row.get("constraint_correctness", "")
            tp = row.get("tp", "")
            if not (constraint_correctness == "TP" and tp == 0):
                print(
                    f"Skipping {response_resource} - {attribute} - {description} As it has been processed before"
                )
                continue

            # Extract previous script information if available
            verification_script = row.get("verification script", None)
            executable_script = row.get("executable script", None)
            status = row.get("status", None)
            confirmation = row.get("script confirmation", None)
            revised_script = row.get("revised script", None)
            revised_executable_script = row.get("revised executable script", None)
            revised_status = row.get("revised status", None)

            print(f"Previous verification script: {verification_script}")
            print(f"Previous executable script: {executable_script}")
            print(f"Previous status: {status}")

            # Get the operation
            operation = corresponding_operation[0]

            # Create script tracking information
            generating_script = {
                "operation": operation,
                "response_resource": response_resource,
                "attribute": attribute,
                "description": description,
                "corresponding_operation": corresponding_operation[0],
                "corresponding_attribute": corresponding_attribute,
                "corresponding_description": corresponding_description,
                "verification_script": "",
                "executable_script": "",
                "status": "",
                "confirmation": "",
                "revised_script": "",
                "revised_executable_script": "",
                "revised_status": "",
            }

            # Check if we've already generated this script
            generated_script = self.track_generated_request_parameter_script(
                generating_script
            )
            if generated_script:
                verification_scripts[index] = generated_script.verification_script
                executable_scripts[index] = generated_script.executable_script
                statuses[index] = generated_script.status
                confirmations[index] = generated_script.confirmation
                revised_scripts[index] = generated_script.revised_script
                revised_executable_scripts[index] = (
                    generated_script.revised_executable_script
                )
                revised_script_statuses[index] = generated_script.revised_status
                continue

            # Get response specification information
            response_specification = self.simplified_openapi[operation].get(
                "responseBody", {}
            )
            response_specification = filter_dict_by_key(
                response_specification, attribute
            )

            # Get response schema structure
            main_response_schema_name, response_type = get_response_body_name_and_type(
                self.openapi_spec, operation
            )
            print(f"Main response schema name: {main_response_schema_name}")
            print(f"Response type: {response_type}")

            if not main_response_schema_name:
                response_schema_structure = response_type
            else:
                if response_type == "object":
                    response_schema_structure = f"{main_response_schema_name} object"
                else:
                    response_schema_structure = (
                        f"array of {main_response_schema_name} objects"
                    )

            # Prepare response schema specification
            response_schema_specification = ""
            if main_response_schema_name:
                response_schema_specification = (
                    f"- Data structure of the response body: {response_schema_structure}\n"
                    f"- Specification of {main_response_schema_name} object: {json.dumps(response_specification)}"
                )
            else:
                response_schema_specification = (
                    f"- Data structure of the response body: {response_schema_structure}\n"
                    f"- Specification: {json.dumps(response_specification)}"
                )

            print(f"Response schema specification: {response_schema_specification}")

            # Extract additional attribute specifications
            attribute_spec = self.simplified_schemas.get(response_resource, {}).get(
                attribute, ""
            )
            other_description = ""

            attribute_spec = (
                self.openapi_spec.get("components", {})
                .get("schemas", {})
                .get(response_resource, {})
                .get("properties", {})
                .get(attribute, "")
            )

            if not attribute_spec:
                attribute_spec = (
                    self.openapi_spec.get("definitions", {})
                    .get(response_resource, {})
                    .get("properties", {})
                    .get(attribute, "")
                )

            if attribute_spec:
                other_description = yaml.dump(attribute_spec)

            # Extract parameter information
            operation_id = corresponding_operation[0]
            cor_operation, path = operation_id.split("-", 1)
            print(
                f"Finding parameter constraints for {corresponding_attribute} in {cor_operation} in corresponding part {corresponding_part} - {path}"
            )

            parameters = (
                self.openapi_spec.get("paths", {})
                .get(path, {})
                .get(cor_operation, {})
                .get(corresponding_part, {})
            )

            parameter_spec = ""
            if corresponding_part == "parameters":
                for parameter in parameters:
                    if parameter["name"] == corresponding_attribute:
                        parameter_spec = yaml.dump(parameter)
                        break
            elif corresponding_part == "requestBody":
                parameter_spec = (
                    parameters.get("content", {})
                    .get("application/x-www-form-urlencoded", {})
                    .get("schema", {})
                    .get("properties", {})
                    .get(corresponding_attribute, {})
                )
                if not parameter_spec:
                    parameter_spec = (
                        parameters.get("content", {})
                        .get("application/json", {})
                        .get("schema", {})
                        .get("properties", {})
                        .get(corresponding_attribute, {})
                    )
                parameter_spec = yaml.dump(parameter_spec)

            # Prepare attribute information
            attribute_information = ""
            if other_description:
                attribute_information = f"-Corresponding attribute {attribute}\n- Description: {other_description}"
            else:
                attribute_information = f"- Corresponding attribute: {attribute}"

            # Generate verification script
            python_verification_script_generation_prompt = (
                CONST_RESPONSEBODY_PARAM_SCRIPT_GEN_PROMPT.format(
                    parameter=corresponding_attribute,
                    parameter_description=parameter_spec,
                    response_schema_specification=response_schema_specification,
                    attribute_information=attribute_information,
                    attribute=attribute,
                )
            )

            # Log prompt to file
            export_file(
                python_verification_script_generation_prompt,
                "python_verification_script_response",
                f"constraint_{index}.txt",
            )

            print(python_verification_script_generation_prompt)

            # Call LLM to generate the verification script
            python_verification_script_response = llm_chat_completion(
                python_verification_script_generation_prompt, model="gpt-4-turbo"
            )

            # Extract the Python code from the response
            python_verification_script = extract_python_code(
                python_verification_script_response
            )

            # Update the arrays with results
            verification_scripts[index] = python_verification_script
            statuses[index] = "unknown"

            # Create a result object and add to tracking
            result = RequestResponseVerificationResult(
                operation=operation,
                response_resource=response_resource,
                attribute=attribute,
                description=description,
                corresponding_operation=corresponding_operation[0],
                corresponding_attribute=corresponding_attribute,
                corresponding_description=corresponding_description,
                verification_script=python_verification_script,
                executable_script="",
                status="unknown",
                confirmation="",
                revised_script="",
                revised_executable_script="",
                revised_status="",
            )

            self.generated_verification_scripts.append(result)

            # Update the dataframe with new values
            self.request_response_constraints_df["verification script"] = pd.array(
                verification_scripts
            )
            self.request_response_constraints_df["executable script"] = pd.array(
                executable_scripts
            )
            self.request_response_constraints_df["status"] = pd.array(statuses)
            self.request_response_constraints_df["script confirmation"] = pd.array(
                confirmations
            )
            self.request_response_constraints_df["revised script"] = pd.array(
                revised_scripts
            )
            self.request_response_constraints_df["revised executable script"] = (
                pd.array(revised_executable_scripts)
            )
            self.request_response_constraints_df["revised status"] = pd.array(
                revised_script_statuses
            )

            # Save the dataframe after each iteration
            self.request_response_constraints_df.to_excel(
                self.request_response_constraints_file, sheet_name="Sheet1", index=False
            )


def main() -> None:
    """
    Main function to run the verification script generation for multiple services.
    """
    # Define the list of service names to process
    service_names: List[str] = [
        "GitLab Groups",
        "GitLab Issues",
        "GitLab Project",
        "GitLab Repository",
        "GitLab Branch",
        "GitLab Commit",
    ]

    # Define the experiment directory and file names
    experiment_dir: str = "approaches/new_method_our_data copy 2"
    excel_file_names: List[str] = [
        "request_response_constraints.xlsx",
        "response_property_constraints.xlsx",
    ]

    # Process each service
    for service_name in service_names:
        try:
            # Define file paths
            response_property_constraints_file = (
                f"{experiment_dir}/{service_name} API/{excel_file_names[1]}"
            )
            request_response_constraints_file = (
                f"{experiment_dir}/{service_name} API/{excel_file_names[0]}"
            )

            # Process request-response constraints if file exists
            if os.path.exists(request_response_constraints_file):
                generator = VerificationScriptGenerator(
                    service_name,
                    experiment_dir,
                    request_response_constraints_file=request_response_constraints_file,
                )
            else:
                print(f"File {request_response_constraints_file} does not exist")

            # Log successful processing
            with open("LOG.txt", "a") as file:
                file.write(f"Successfully processed {service_name}\n")

        except Exception as e:
            print(f"Error processing {service_name}: {e}")
            with open("LOG.txt", "a") as file:
                file.write(f"Error processing {service_name}: {e}\n")


if __name__ == "__main__":
    main()
