# /src/response_body_verification/data_model_buiding.py

"""
Data Model Building Module

This module provides functionality to build data models from OpenAPI specifications
by analyzing schema relationships and identifying key fields.

The data models created help in understanding the relationships between different entities
in an API and can be used for generating test cases, validation rules, or documentation.
"""

import json
import os
from typing import Dict, List, Optional, Set, Any


from utils.openapi_utils import (
    load_openapi,
    get_operation_params,
    get_simplified_schema,
    get_relevant_schemas_of_operation,
)
from utils.gptcall import GPTChatCompletion
from utils.text_extraction import extract_data_model_key_pairs
from constant import FIND_SCHEMA_KEYS, DATA_MODEL_PROMPT

from models.data_building_models import (
    DataModel,
    DataModelBuilderConfig,
    SchemaKeyPair,
    SchemaRelationship,
)


class DataModelBuilder:
    """
    Builds data models from OpenAPI specifications by analyzing schema relationships.

    This class analyzes OpenAPI specifications to identify relationships between different
    schemas and builds a comprehensive data model that can be used for various purposes
    such as test case generation or documentation.

    Attributes:
        config: Configuration settings for the builder
        openapi_spec: Loaded OpenAPI specification
        simplified_openapi: Simplified representation of the OpenAPI operations
        simplified_schemas: Simplified representation of the schema definitions
        service_name: Name of the API service
        operation_sequences: Extracted operation sequences for dependency analysis
        data_model: Built data model with schema keys and relationships
    """

    def __init__(
        self,
        openapi_path: str,
        ks_project_path: Optional[str] = None,
        data_types_to_keep: Optional[Set[str]] = None,
    ) -> None:
        """
        Initialize the DataModelBuilder.

        Args:
            openapi_path: Path to the OpenAPI specification file
            ks_project_path: Path to the KS project directory containing operation sequences
            data_types_to_keep: Set of data types to keep during attribute filtering
                               (defaults to "integer" and "string")
        """
        # Create configuration
        self.config = DataModelBuilderConfig(
            openapi_path=openapi_path,
            ks_project_path=ks_project_path,
            data_types_to_keep=data_types_to_keep or {"integer", "string"},
        )

        # Load OpenAPI specification
        self.openapi_spec: Dict[str, Any] = load_openapi(openapi_path)
        self.simplified_openapi: Dict[str, Any] = get_operation_params(
            self.openapi_spec, get_description=True, get_response_body=False
        )
        self.simplified_schemas: Dict[str, Any] = get_simplified_schema(
            self.openapi_spec
        )

        # Initialize service name
        self.service_name: str = self.openapi_spec["info"]["title"]

        # Initialize operation sequences
        self.operation_sequences: Dict[str, List[List[str]]] = {}

        # Initialize data model
        self.data_model = DataModel()

        # Execute the building process
        self.initialize()
        self.filter_attributes()
        self.building_data_model()

    def initialize(self) -> None:
        """
        Initialize by loading operation sequences if available.

        This method loads operation sequences from the KS project path if provided.
        Operation sequences represent dependencies between API operations.

        Raises:
            FileNotFoundError: If the operation sequences file doesn't exist
            json.JSONDecodeError: If the operation sequences file contains invalid JSON
        """
        if self.config.ks_project_path:
            odg_output_dir = os.path.join(
                self.config.ks_project_path,
                "KAT Plugin",
                self.service_name,
                "operation_sequences.json",
            )

            try:
                with open(odg_output_dir, "r") as f:
                    self.operation_sequences = json.load(f)
            except FileNotFoundError:
                print(
                    f"Warning: Operation sequences file not found at {odg_output_dir}"
                )
                self.operation_sequences = {}
            except json.JSONDecodeError:
                print(
                    f"Warning: Invalid JSON in operation sequences file at {odg_output_dir}"
                )
                self.operation_sequences = {}

    def filter_attributes(self) -> None:
        """
        Filter out attributes that don't have the desired data types.

        This method removes attributes from the simplified schemas that don't have
        the data types specified in config.data_types_to_keep (default: integer, string).
        This helps focus the analysis on attributes that are more likely to be key fields.
        """
        for schema_name, schema_attrs in list(self.simplified_schemas.items()):
            if not schema_attrs:  # Skip empty schemas
                continue

            # Track attributes to remove
            attrs_to_remove: List[str] = []

            for attr_name, attr_value in schema_attrs.items():
                if isinstance(attr_value, str):
                    # Check if the attribute has one of the target data types
                    has_target_type = False
                    for data_type in self.config.data_types_to_keep:
                        if data_type in attr_value:
                            has_target_type = True
                            break

                    if not has_target_type:
                        attrs_to_remove.append(attr_name)
                else:
                    # Non-string attributes should be removed
                    attrs_to_remove.append(attr_name)

            # Remove unwanted attributes
            for attr_name in attrs_to_remove:
                schema_attrs.pop(attr_name, None)

    def building_data_model(self) -> None:
        """
        Build the data model by analyzing schema relationships and key fields.

        This method:
        1. Identifies key fields for each schema using GPT
        2. Analyzes relationships between schemas
        3. Finds field mappings between related schemas

        The resulting data model contains information about schema keys and
        relationships between schemas.
        """
        # Initialize data model structure
        self.data_model = DataModel()

        # Collect relevant schemas from all operations
        schemas: List[str] = []
        for operation in self.simplified_openapi:
            # Get schemas directly referenced in the operation
            _, relevant_schemas = get_relevant_schemas_of_operation(
                operation, self.openapi_spec
            )
            schemas.extend(relevant_schemas)

            # Get schemas referenced in dependent operations
            sequences = self.operation_sequences.get(operation, [])
            for sequence in sequences:
                for child_operation in sequence:
                    _, child_schemas = get_relevant_schemas_of_operation(
                        child_operation, self.openapi_spec
                    )
                    schemas.extend(child_schemas)

        # Remove duplicates
        unique_schemas = list(set(schemas))

        # Find and store key fields for each schema
        for schema in unique_schemas:
            if (
                schema not in self.simplified_schemas
                or not self.simplified_schemas[schema]
            ):
                continue

            # Generate prompt to find schema keys
            prompt = FIND_SCHEMA_KEYS.format(
                schema_specification=json.dumps(self.simplified_schemas[schema])
            )

            # Get response from GPT
            response = GPTChatCompletion(prompt, system="")

            if response:
                # Parse the keys from the response
                keys = [key.strip() for key in response.split(",")]
                # Validate that the keys exist in the schema
                valid_keys = [
                    key for key in keys if key in self.simplified_schemas[schema]
                ]

                if valid_keys:
                    self.data_model.schema_keys[schema] = valid_keys

        # Analyze relationships between schemas
        for i in range(len(unique_schemas)):
            for j in range(i + 1, len(unique_schemas)):
                schema1 = unique_schemas[i]
                schema2 = unique_schemas[j]

                # Skip if either schema has no attributes
                if (
                    schema1 not in self.simplified_schemas
                    or schema2 not in self.simplified_schemas
                    or not self.simplified_schemas[schema1]
                    or not self.simplified_schemas[schema2]
                ):
                    continue

                # Check if this schema pair is already analyzed
                pair_exists = False
                for relationship in self.data_model.schema_relationships:
                    if relationship.schema_pair == (
                        schema1,
                        schema2,
                    ) or relationship.schema_pair == (schema2, schema1):
                        pair_exists = True
                        break

                if pair_exists:
                    continue

                # Format schemas for the prompt
                schema1_str = f"{schema1}\n{self.simplified_schemas[schema1]}"
                schema2_str = f"{schema2}\n{self.simplified_schemas[schema2]}"

                # Generate prompt to find field mappings
                data_model_prompt = DATA_MODEL_PROMPT.format(
                    schema_1=schema1_str, schema_2=schema2_str
                )

                # Get response from GPT
                data_model_response = GPTChatCompletion(
                    data_model_prompt, system="", temperature=0.0
                )

                # Extract field mappings from the response
                if data_model_response:
                    key_pairs = extract_data_model_key_pairs(data_model_response)

                    if key_pairs:
                        # Create schema relationship
                        field_mappings = [
                            SchemaKeyPair(source_field=src, target_field=tgt)
                            for src, tgt in key_pairs
                        ]

                        self.data_model.schema_relationships.append(
                            SchemaRelationship(
                                schema_pair=(schema1, schema2),
                                field_mappings=field_mappings,
                            )
                        )

    def get_data_model(self) -> DataModel:
        """
        Get the built data model.

        Returns:
            DataModel object containing schema keys and relationships
        """
        return self.data_model

    def save_data_model(self, output_path: str) -> None:
        """
        Save the data model to a JSON file.

        Args:
            output_path: Path where the data model will be saved

        Returns:
            None
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Convert to legacy format for backward compatibility
        legacy_format = self.data_model.to_legacy_format()

        # Save to file
        with open(output_path, "w") as f:
            json.dump(legacy_format, f, indent=2)


def main() -> None:
    """
    Entry point for testing the DataModelBuilder.

    This function creates a DataModelBuilder for the Petstore API
    and saves the resulting data model to a file.
    """
    # Create data model builder for Petstore API
    data_model_builder = DataModelBuilder("response-verification/openapi/Petstore.json")

    # Save the data model
    experiment_dir = "experiment"
    os.makedirs(experiment_dir, exist_ok=True)
    output_path = os.path.join(
        experiment_dir, f"{data_model_builder.service_name}_data_model.json"
    )

    data_model_builder.save_data_model(output_path)
    print(f"Data model saved to {output_path}")


if __name__ == "__main__":
    main()
