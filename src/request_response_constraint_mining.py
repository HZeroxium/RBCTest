# /src/request_response_constraint_mining.py

"""
Request-Response Constraint Mining Module

This module extracts constraints from request parameters and maps relationships
between request parameters and response bodies in REST API specifications.
"""

import os
import json
from dotenv import load_dotenv
import openai
from response_body_verification import ConstraintExtractor, ParameterResponseMapper

from utils import load_openapi, convert_json_to_excel_response_property_constraints

# Load environment variables and set up OpenAI API
load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY")

# Constants
EXPERIMENT_FOLDER = "experiment_our"
DATASET_BASE_PATH = "RBCTest_dataset"


def main() -> None:
    """
    Main function to extract constraints from request parameters and map relationships
    between request parameters and response bodies.

    This function processes OpenAPI specifications to identify input parameter constraints
    and maps how request parameters influence response properties.
    """
    experiment_folder = EXPERIMENT_FOLDER

    # List of REST services to analyze
    rest_services = ["Spotify getArtistAlbums"]

    for rest_service in rest_services:
        print("\n" + "*" * 20)
        print(rest_service)
        print("*" * 20)

        # Construct path to OpenAPI specification
        openapi_path = f"{DATASET_BASE_PATH}/{rest_service}/openapi.json"

        # Load and parse OpenAPI specification
        openapi_spec = load_openapi(openapi_path)

        # Extract service name from specification
        service_name = openapi_spec["info"]["title"]

        # Create output directory if it doesn't exist
        os.makedirs(f"{experiment_folder}/{service_name}", exist_ok=True)

        # Initialize constraint extractor based on service type
        if rest_service == "StripeClone":
            # Skip StripeClone specific handling as it's commented out in original code
            pass
            # Original comment preserved:
            # constraint_extractor = ConstraintExtractor(
            #     openapi_path, save_and_load=False, list_of_operations=selected_operations)
        else:
            # Default handling for other services
            constraint_extractor = ConstraintExtractor(
                openapi_path, save_and_load=False
            )

        # Extract input parameter constraints
        input_param_outfile = f"{experiment_folder}/{service_name}/input_parameter.json"
        constraint_extractor.get_input_parameter_constraints(
            outfile=input_param_outfile
        )

        # Save input parameter constraints to JSON file
        with open(input_param_outfile, "w") as f:
            json.dump(constraint_extractor.input_parameter_constraints, f, indent=2)

        # Extract request-response mapping constraints
        req_resp_outfile = (
            f"{experiment_folder}/{service_name}/request_response_constraints.json"
        )

        # Map request parameters to response properties
        parameterResponseMapper = ParameterResponseMapper(
            openapi_path, save_and_load=False, outfile=req_resp_outfile
        )

        # Save request-response mappings to JSON file
        with open(req_resp_outfile, "w") as f:
            json.dump(
                parameterResponseMapper.response_body_input_parameter_mappings,
                f,
                indent=2,
            )

        # Convert JSON results to Excel format
        convert_json_to_excel_response_property_constraints(
            req_resp_outfile, openapi_path, req_resp_outfile.replace(".json", ".xlsx")
        )


if __name__ == "__main__":
    main()
