# /src/response_property_constraint_mining_ablation.py

"""
Response Property Constraint Mining - Ablation Study

This module implements an ablation study for constraint mining using a naive approach.
It extracts response property constraints from OpenAPI specifications for comparison
with the main approach.
"""

import os
import json
from dotenv import load_dotenv
import openai
from response_body_verification import ConstraintExtractor

from utils import load_openapi, load_file_lines

# Load environment variables and set up OpenAI API
load_dotenv()
openai.api_key = os.getenv("OPENAI_KEY")

# Constants
EXPERIMENT_FOLDER = "experiment_naive"
DATASET_BASE_PATH = "RBCTest_dataset"
STRIPE_SCHEMAS_PATH = "src/stripe_selected/selected_schemas.txt"
STRIPE_OPERATIONS_PATH = "src/stripe_selected/selected_operations.txt"


def main() -> None:
    """
    Main function for the ablation study of response property constraint mining.

    This function implements a naive approach to constraint extraction from
    REST API specifications for comparison with the main approach.
    """
    experiment_folder = EXPERIMENT_FOLDER

    # List of REST services to analyze in the ablation study
    rest_services = [
        "Canada Holidays",
        "GitLab Branch",
        "GitLab Project",
        "GitLab Repository",
        "GitLab Commit",
        "GitLab Groups",
        "GitLab Issues",
        "StripeClone",
    ]

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

        # Extract constraints using naive approach based on service type
        if rest_service == "StripeClone":
            # Special handling for StripeClone with selected operations
            constraint_extractor = ConstraintExtractor(
                openapi_path,
                save_and_load=False,
                list_of_operations=selected_operations,
            )
            # Use naive approach for constraint extraction
            constraint_extractor.get_inside_response_body_constraints_naive(
                outfile=outfile, selected_schemas=selected_schemas
            )
            # Save extracted constraints to JSON file
            with open(outfile, "w") as f:
                json.dump(
                    constraint_extractor.inside_response_body_constraints, f, indent=2
                )
        else:
            # Default handling for other services
            constraint_extractor = ConstraintExtractor(
                openapi_path, save_and_load=False
            )
            # Use naive approach for constraint extraction
            constraint_extractor.get_inside_response_body_constraints_naive(
                outfile=outfile
            )
            # Save extracted constraints to JSON file
            with open(outfile, "w") as f:
                json.dump(
                    constraint_extractor.inside_response_body_constraints, f, indent=2
                )


if __name__ == "__main__":
    main()
