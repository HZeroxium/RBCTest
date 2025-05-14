# /src/verifier.py

"""
Constraint Verification Module

This module verifies constraints against API responses. It processes constraint
definitions from Excel files and runs verification scripts against example values
to determine if the constraints are satisfied.
"""

import os
import random
import pandas as pd
from typing import List, Optional

from verifier.find_example_utils import find_example_value, load_openapi_spec
from utils.verification_utils import (
    response_property_constraint_verify,
    request_response_constraint_verify,
)
from utils.execution_utils import get_api_responses
from utils.openapi_example_finder import (
    load_openapi_spec,
)
from models.verification_models import (
    VerificationConfig,
    ConstraintVerificationResult,
    FieldVerificationResult,
)


class ConstraintVerifier:
    """
    Verifies constraints against API responses.

    This class processes constraint definitions from Excel files and
    verifies them against API responses to determine if they are satisfied.
    """

    def __init__(self, config: VerificationConfig) -> None:
        """
        Initialize the constraint verifier.

        Args:
            config: Configuration parameters for the verifier

        Returns:
            None
        """
        self.config = config
        self.count_example_found = 0
        self.count_all_constraints = 0

        # Ensure the code directory exists
        os.makedirs("code", exist_ok=True)

    def get_api_folders(self) -> List[str]:
        """
        Get the list of API folders to process.

        Returns:
            List of API folder names
        """
        return [
            f
            for f in os.listdir(self.config.root_folder)
            if os.path.isdir(os.path.join(self.config.root_folder, f))
        ]

    def verify_constraints(self, api_filter: Optional[str] = None) -> None:
        """
        Verify constraints for all APIs or a specific API.

        Args:
            api_filter: Optional API name filter

        Returns:
            None
        """
        apis = self.get_api_folders()

        print(f"Start verifying constraints for: {apis}")

        for api in apis:
            if api_filter and api_filter not in api:
                continue

            self._verify_api_constraints(api)

        print(
            f"Found example value for {self.count_example_found}/{self.count_all_constraints} constraints"
        )

    def _verify_api_constraints(self, api: str) -> None:
        """
        Verify constraints for a specific API.

        Args:
            api: The API name

        Returns:
            None
        """
        api_folder = os.path.join(self.config.root_folder, api)

        # Get API responses and related files
        api_responses = get_api_responses(
            os.path.join(self.config.api_spec_folder, api.replace(" API", ""))
        )

        # Sample responses if there are too many
        if len(api_responses) > 10:
            api_responses = random.sample(api_responses, 10)

        # Construct paths for request parameters and bodies
        request_params = [
            os.path.join(
                self.config.api_spec_folder,
                api.replace(" API", ""),
                "queryParameters",
                os.path.basename(f),
            )
            for f in api_responses
        ]

        request_bodies = [
            os.path.join(
                self.config.api_spec_folder,
                api.replace(" API", ""),
                "bodyParameters",
                os.path.basename(f),
            )
            for f in api_responses
        ]

        # Verify response property constraints
        response_constraints_file = os.path.join(
            api_folder, "response_property_constraints.xlsx"
        )
        if os.path.exists(response_constraints_file):
            self._verify_response_property_constraints(
                response_constraints_file, api, api_responses
            )

        # Verify request-response constraints
        request_response_constraints_file = os.path.join(
            api_folder, "request_response_constraints.xlsx"
        )
        if os.path.exists(request_response_constraints_file):
            self._verify_request_response_constraints(
                request_response_constraints_file,
                api,
                api_responses,
                request_params,
                request_bodies,
            )

    def _verify_response_property_constraints(
        self, constraints_file: str, api: str, api_responses: List[str]
    ) -> None:
        """
        Verify response property constraints for an API.

        Args:
            constraints_file: Path to the constraints file
            api: The API name
            api_responses: List of API response files

        Returns:
            None
        """
        df = pd.read_excel(constraints_file)

        # Add columns for example values and verification results if they don't exist
        if "Example_value" not in df.columns:
            df["Example_value"] = None

        if "verify_result" not in df.columns:
            df["verify_result"] = None

        # Load OpenAPI specification
        openapi_spec_file = os.path.join(
            self.config.api_spec_folder, api.replace(" API", ""), "openapi.json"
        )
        openapi_spec = load_openapi_spec(openapi_spec_file)

        # Process each constraint
        for index, row in df.iterrows():
            object_name = row["response resource"]
            field_name = row["attribute"]

            # Find example value
            example_value = find_example_value(openapi_spec, object_name, field_name)
            df.at[index, "Example_value"] = str(example_value)

            self.count_all_constraints += 1

            # Verify constraint if example value is found
            if example_value is not None:
                self.count_example_found += 1

                # Get the verification script and execute it if available
                python_code = row.get("verification script")
                df.at[index, "verify_result"] = 1

                if python_code is not None and not pd.isna(python_code):
                    for api_response in api_responses:
                        try:
                            with open(api_response, "r", encoding="utf-8") as f:
                                api_response_text = f.read()

                            result = response_property_constraint_verify(
                                python_code,
                                field_name,
                                example_value,
                                api_response_text,
                            )

                            if result == "-1":
                                df.at[index, "verify_result"] = 0
                                break
                        except Exception as e:
                            print(
                                f"Error verifying {field_name} in {api_response}: {e}"
                            )

        # Save updated dataframe
        df.to_excel(constraints_file, index=False)

    def _verify_request_response_constraints(
        self,
        constraints_file: str,
        api: str,
        api_responses: List[str],
        request_params: List[str],
        request_bodies: List[str],
    ) -> None:
        """
        Verify request-response constraints for an API.

        Args:
            constraints_file: Path to the constraints file
            api: The API name
            api_responses: List of API response files
            request_params: List of request parameter files
            request_bodies: List of request body files

        Returns:
            None
        """
        df = pd.read_excel(constraints_file)

        # Add columns for example values and verification results if they don't exist
        if "Example_value" not in df.columns:
            df["Example_value"] = None

        if "verify_result" not in df.columns:
            df["verify_result"] = None

        # Load OpenAPI specification
        openapi_spec_file = os.path.join(
            self.config.api_spec_folder, api.replace(" API", ""), "openapi.json"
        )
        openapi_spec = load_openapi_spec(openapi_spec_file)

        # Process each constraint
        for index, row in df.iterrows():
            object_name = row["response resource"]
            field_name = row["attribute"]

            # Find example value
            example_value = find_example_value(openapi_spec, object_name, field_name)
            df.at[index, "Example_value"] = str(example_value)

            request_info_part = row["part"]

            # Determine which request files to use based on the part
            if request_info_part == "requestBody":
                request_informations = request_bodies
            else:
                request_informations = request_params

            self.count_all_constraints += 1

            # Verify constraint if example value is found
            if example_value is not None:
                self.count_example_found += 1

                # Get the verification script and request parameter
                python_code = row.get("verification script")
                request_param = row["corresponding attribute"]

                if python_code is not None and not pd.isna(python_code):
                    df.at[index, "verify_result"] = 1

                    # Check each response against its corresponding request
                    for api_response, request_information in zip(
                        api_responses, request_informations
                    ):
                        try:
                            # Read API response file
                            with open(api_response, "r", encoding="utf-8") as f:
                                api_response_text = f.read()

                            # Read request information file if it exists
                            request_information_text = "{}"
                            if os.path.exists(request_information):
                                with open(
                                    request_information, "r", encoding="utf-8"
                                ) as f:
                                    request_information_text = f.read()

                            # Verify the constraint
                            result = request_response_constraint_verify(
                                python_code,
                                request_information_text,
                                request_param,
                                field_name,
                                example_value,
                                api_response_text,
                            )

                            # Update result if constraint is not satisfied
                            if result == "-1":
                                df.at[index, "verify_result"] = 0
                                break
                        except Exception as e:
                            print(
                                f"Error verifying {field_name} in {api_response}: {e}"
                            )

        # Save updated dataframe
        df.to_excel(constraints_file, index=False)


def main() -> None:
    """
    Main entry point for constraint verification.

    This function sets up the verification configuration and runs the
    constraint verification process.
    """
    # Configure the verifier
    config = VerificationConfig(
        root_folder="approaches/rbctest_our_data",
        api_spec_folder="RBCTest_dataset",
        executable="python",
    )

    # Create and run the verifier
    verifier = ConstraintVerifier(config)
    verifier.verify_constraints(api_filter="Can")


if __name__ == "__main__":
    main()
