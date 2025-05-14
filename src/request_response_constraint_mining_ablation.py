# /src/request_response_constraint_mining_ablation.py

"""
Request-Response Constraint Mining - Ablation Study

This module implements an ablation study for request-response constraint mining.
It extracts relationships between request parameters and response properties,
and evaluates the results against ground truth data.
"""

import os
import json
from typing import List
from dotenv import load_dotenv
import openai
from response_body_verification import ConstraintExtractor, ParameterResponseMapper

from utils import load_openapi, convert_json_to_excel_request_response_constraints
from eval.request_approach_evaluate import evaluate_request_response_constraint_mining


# Load environment variables and set up OpenAI API
load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY")

# Constants
EXPERIMENT_FOLDER = "experiment_our"
GROUND_TRUTH_FOLDER = "approaches/ground_truth"
DATASET_BASE_PATH = "RBCTest_dataset"
STRIPE_OPERATIONS_PATH = "stripe_selected/selected_operations"
STRIPE_SCHEMAS_PATH = "src/selected_schemas.txt"
STRIPE_SCHEMAS_JSON_PATH = "response-verification/stripe_schemas.json"


def main() -> None:
    """
    Main function for the ablation study of request-response constraint mining.

    This function extracts request-response relationships, saves the results,
    and evaluates the extraction against ground truth data.
    """
    experiment_folder = EXPERIMENT_FOLDER
    ground_truth_folder = GROUND_TRUTH_FOLDER

    # List of REST services to analyze in the ablation study
    rest_services = [
        "GitLab Branch",
        "GitLab Project",
        "GitLab Repository",
        "GitLab Commit",
        "GitLab Groups",
        "GitLab Issues",
        "Canada Holidays",
        "StripeClone",
    ]

    # Load selected operations and schemas for Stripe service
    selected_operations = _load_file_lines(STRIPE_OPERATIONS_PATH)
    selected_schemas = _load_file_lines(STRIPE_SCHEMAS_PATH)

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
            # Special handling for StripeClone with selected operations
            constraint_extractor = ConstraintExtractor(
                openapi_path,
                save_and_load=False,
                list_of_operations=selected_operations,
            )
        else:
            # Default handling for other services
            constraint_extractor = ConstraintExtractor(
                openapi_path, save_and_load=False
            )

        # Extract input parameter constraints
        outfile = (
            f"{experiment_folder}/{service_name}/response_property_constraints.json"
        )
        constraint_extractor.get_input_parameter_constraints(outfile=outfile)

        # Save input parameter constraints to JSON file
        with open(outfile, "w") as f:
            json.dump(constraint_extractor.input_parameter_constraints, f, indent=2)

        # Load Stripe schemas from JSON
        list_of_schemas = json.load(open(STRIPE_SCHEMAS_JSON_PATH, "r"))

        # Extract request-response mapping constraints
        outfile = (
            f"{experiment_folder}/{service_name}/request_response_constraints.json"
        )

        # Map request parameters to response properties
        parameterResponseMapper = ParameterResponseMapper(
            openapi_path, save_and_load=False, outfile=outfile
        )

        # Save request-response mappings to JSON file
        with open(outfile, "w") as f:
            json.dump(
                parameterResponseMapper.response_body_input_parameter_mappings,
                f,
                indent=2,
            )

        # Convert JSON results to Excel format
        convert_json_to_excel_request_response_constraints(
            outfile, openapi_path, outfile.replace(".json", ".xlsx")
        )

        # Evaluate extraction results against ground truth
        evaluate_request_response_constraint_mining(
            experiment_folder,
            ground_truth_folder,
            [service_name],
            f"{experiment_folder}/evaluation.csv",
            export=True,
        )


def _load_file_lines(file_path: str) -> List[str]:
    """
    Load lines from a file and strip whitespace.

    Args:
        file_path: Path to the file to be loaded

    Returns:
        List of stripped lines from the file
    """
    with open(file_path, "r") as f:
        lines = f.readlines()
    return [line.strip() for line in lines]


if __name__ == "__main__":
    main()
