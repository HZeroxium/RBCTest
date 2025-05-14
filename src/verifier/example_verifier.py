"""
Example Verifier Module

This module provides functionality to verify and add example values to
constraint files for API specifications.
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import pandas as pd

from models.example_models import VerifierConfig, VerifierResult, ExampleSearchOptions
from utils.openapi_example_finder import OpenAPIExampleFinder, load_openapi_spec


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("example_verifier.log"),
    ],
)
logger = logging.getLogger("example_verifier")


class ExampleVerifier:
    """
    A class for verifying and adding example values to constraint files.

    This class processes API specifications to find example values for fields
    in constraint files and updates those files with the found values.
    """

    def __init__(self, config: VerifierConfig):
        """
        Initialize the ExampleVerifier.

        Args:
            config: Configuration for the verifier
        """
        self.config = config
        self.result = VerifierResult()

    def process_apis(self) -> VerifierResult:
        """
        Process all APIs in the root folder.

        Returns:
            VerifierResult containing statistics about the processing
        """
        # Find all API folders
        api_folders = [
            f
            for f in os.listdir(self.config.root_folder)
            if os.path.isdir(os.path.join(self.config.root_folder, f))
        ]

        logger.info(f"Found {len(api_folders)} APIs to process")

        # Process each API
        for api in api_folders:
            self._process_api(api)
            self.result.apis_processed.append(api)

        # Calculate final statistics
        self.result.calculate_stats()
        logger.info(str(self.result))

        return self.result

    def _process_api(self, api_name: str) -> None:
        """
        Process a single API by finding example values for its constraints.

        Args:
            api_name: Name of the API to process
        """
        logger.info(f"Processing API: {api_name}")

        # Define file paths
        api_folder = self.config.root_folder / api_name
        response_constraints_file = api_folder / "response_property_constraints.xlsx"
        request_response_constraints_file = (
            api_folder / "request_response_constraints.xlsx"
        )

        # Load OpenAPI spec
        api_spec_name = api_name.replace(" API", "")
        openapi_spec_file = self.config.api_spec_folder / api_spec_name / "openapi.json"

        try:
            openapi_spec = load_openapi_spec(openapi_spec_file)
            finder = OpenAPIExampleFinder(openapi_spec, self.config.search_options)

            # Process response property constraints if they exist
            if response_constraints_file.exists():
                self._process_constraint_file(response_constraints_file, finder)

            # Process request-response constraints if they exist
            if request_response_constraints_file.exists():
                self._process_constraint_file(request_response_constraints_file, finder)

        except Exception as e:
            logger.error(f"Error processing API {api_name}: {e}")

    def _process_constraint_file(
        self, constraint_file: Path, finder: OpenAPIExampleFinder
    ) -> None:
        """
        Process a constraint file by finding example values for each constraint.

        Args:
            constraint_file: Path to the constraint file
            finder: OpenAPIExampleFinder instance to use for finding examples
        """
        logger.info(f"Processing constraint file: {constraint_file}")

        try:
            # Load the constraint file
            df = pd.read_excel(constraint_file)

            # Add Example_value column if it doesn't exist
            if "Example_value" not in df.columns:
                df["Example_value"] = None

            # Process each row
            for index, row in df.iterrows():
                object_name = row["response resource"]
                field_name = row["attribute"]

                # Find example value
                search_result = finder.find_example_value(object_name, field_name)

                # Update statistics
                self.result.total_constraints += 1
                if search_result.found:
                    self.result.examples_found += 1

                # Update dataframe
                df.at[index, "Example_value"] = str(search_result.example_value)

                # Log progress periodically
                if index % 10 == 0 and index > 0:
                    logger.debug(
                        f"Processed {index} constraints in {constraint_file.name}"
                    )

            # Save the updated dataframe
            output_file = constraint_file.with_name(
                f"{constraint_file.stem}{self.config.output_suffix}{constraint_file.suffix}"
            )
            df.to_excel(output_file, index=False)
            logger.info(f"Saved updated constraints to {output_file}")

        except Exception as e:
            logger.error(f"Error processing constraint file {constraint_file}: {e}")
            raise


def main() -> None:
    """
    Main entry point for the script.

    Parses command line arguments and runs the verifier.
    """
    parser = argparse.ArgumentParser(
        description="Find example values for API constraints"
    )
    parser.add_argument(
        "--root-folder",
        type=str,
        default="approaches/rbctest_our_data",
        help="Root folder containing API data",
    )
    parser.add_argument(
        "--api-spec-folder",
        type=str,
        default="RBCTest_dataset",
        help="Folder containing API specifications",
    )
    parser.add_argument(
        "--output-suffix",
        type=str,
        default="_example_value",
        help="Suffix to add to output files",
    )
    parser.add_argument(
        "--no-brute-force",
        action="store_true",
        help="Disable brute force search",
    )

    args = parser.parse_args()

    # Create configuration
    search_options = ExampleSearchOptions(
        use_brute_force=not args.no_brute_force,
    )

    config = VerifierConfig(
        root_folder=Path(args.root_folder),
        api_spec_folder=Path(args.api_spec_folder),
        output_suffix=args.output_suffix,
        search_options=search_options,
    )

    # Run the verifier
    verifier = ExampleVerifier(config)
    result = verifier.process_apis()

    # Print final results
    print(f"\nProcessed {len(result.apis_processed)} APIs")
    print(str(result))


if __name__ == "__main__":
    # For backward compatibility, use the hardcoded values if run directly
    root_folder = "approaches/rbctest_our_data"
    api_spec_folder = "RBCTest_dataset"

    # Create configuration with default values
    config = VerifierConfig.from_strings(root_folder, api_spec_folder)

    # Run the verifier
    verifier = ExampleVerifier(config)
    result = verifier.process_apis()

    # Print final result
    print(f"\nProcessed {len(result.apis_processed)} APIs")
    print(
        f"Found example value for {result.examples_found}/{result.total_constraints} "
        f"constraints ({100 - result.failure_rate:.1f}% success rate)"
    )
