# /src/response_property_constraint_mining.py

"""
Response Property Constraint Mining Module

This module extracts constraints from response bodies in REST API specifications.
It analyzes OpenAPI specifications to identify and document constraints that
response properties must satisfy.
"""

import os
import json
from dotenv import load_dotenv
import openai
from response_body_verification import ConstraintExtractor

from utils import (
    load_openapi,
    load_file_lines,
    convert_json_to_excel_response_property_constraints,
)

from eval.response_approach_evaluate import evaluate_response_property_constraint_mining

# Load environment variables and set up OpenAI API
load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY")

# Constants
EXPERIMENT_FOLDER = "experiment_our"
GROUND_TRUTH_FOLDER = "approaches/ground_truth"
DATASET_BASE_PATH = "RBCTest_dataset"
STRIPE_SCHEMAS_PATH = "src/stripe_selected/selected_schemas.txt"
STRIPE_OPERATIONS_PATH = "src/stripe_selected/selected_operations.txt"


def main() -> None:
    """
    Main function to extract response property constraints from REST API specifications.

    This function processes OpenAPI specifications to extract constraints on response
    properties, saves the results in JSON and Excel formats, and evaluates the
    extraction against ground truth.
    """
    experiment_folder = EXPERIMENT_FOLDER
    ground_truth_folder = GROUND_TRUTH_FOLDER

    # List of REST services to analyze
    rest_services = ["Spotify getArtistAlbums"]

    # Load selected schemas and operations for Stripe service
    selected_schemas = load_file_lines(STRIPE_SCHEMAS_PATH)
    selected_operations = load_file_lines(STRIPE_OPERATIONS_PATH)

    for rest_service in rest_services:
        print("*" * 20)
        print(rest_service)
        print("*" * 20)
        # Construct path to OpenAPI specification
        openapi_path = f"{DATASET_BASE_PATH}/{rest_service}/openapi.json"

        # Load and parse OpenAPI specification
        openapi_spec = load_openapi(openapi_path)
        print(openapi_spec)

        # Extract service name from specification
        service_name = openapi_spec["info"]["title"]

        # Create output directory if it doesn't exist
        os.makedirs(f"{experiment_folder}/{service_name}", exist_ok=True)

        # Define output file path
        outfile = (
            f"{experiment_folder}/{service_name}/response_property_constraints.json"
        )

        # Extract constraints based on service type
        if rest_service == "StripeClone":
            # Special handling for StripeClone with selected operations
            constraint_extractor = ConstraintExtractor(
                openapi_path,
                save_and_load=False,
                list_of_operations=selected_operations,
            )
            constraint_extractor.get_inside_response_body_constraints(
                outfile=outfile, selected_schemas=selected_schemas
            )
        else:
            # Default handling for other services
            constraint_extractor = ConstraintExtractor(
                openapi_path, save_and_load=False
            )
            constraint_extractor.get_inside_response_body_constraints(outfile=outfile)

        # Save extracted constraints to JSON file
        with open(outfile, "w") as f:
            json.dump(
                constraint_extractor.inside_response_body_constraints, f, indent=2
            )

        # Convert JSON results to Excel format
        convert_json_to_excel_response_property_constraints(
            outfile, openapi_path, outfile.replace(".json", ".xlsx")
        )

        # Evaluate extraction results against ground truth
        evaluate_response_property_constraint_mining(
            experiment_folder,
            ground_truth_folder,
            [service_name],
            f"{experiment_folder}/evaluation.csv",
            export=True,
        )


if __name__ == "__main__":
    main()
