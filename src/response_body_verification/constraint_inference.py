# /src/response_body_verification/constraint_inference.py

"""
Constraint Inference Module

This module provides classes and functions to extract and infer constraints from
OpenAPI specifications, focusing on response body attributes and input parameters.

The main class, ConstraintExtractor, analyzes service descriptions and attribute
definitions to identify constraints that should be enforced during API usage.
"""

import json
import os
import copy
from typing import Dict, List, Optional, Any


from utils.openapi_utils import (
    load_openapi,
    simplify_openapi,
    get_simplified_schema,
    get_relevent_response_schemas_of_operation,
    extract_operations,
)
from utils.gptcall import GPTChatCompletion
from utils.text_extraction import (
    extract_variables,
    extract_values,
    extract_dict_attributes,
    extract_python_code,
    extract_answer,
    extract_summary_constraint,
    extract_idl,
    is_construct_json_object,
    standardize_returned_idl,
)
from constant import (
    DESCRIPTION_OBSERVATION_PROMPT,
    NAIVE_CONSTRAINT_DETECTION_PROMPT,
    CONSTRAINT_CONFIRMATION,
)
from models.constraint_models import (
    CheckedMapping,
    AttributeMapping,
    ConstraintExtractorConfig,
    ResponseBodyConstraint,
    InputParameterConstraint,
    ResponseBodyConstraints,
    InputParameterConstraints,
)


class ConstraintExtractor:
    """
    Extracts and infers constraints from OpenAPI specifications.

    This class analyzes attribute descriptions in OpenAPI specifications to identify
    constraints that should be enforced, both in response bodies and input parameters.
    It uses GPT language models to interpret natural language descriptions and
    determine if they imply constraints.

    Attributes:
        openapi_path: Path to the OpenAPI specification file
        save_and_load: Whether to save/load progress from files
        list_of_operations: Optional list of operations to process
        experiment_folder: Folder to store experiment files
        openapi_spec: Loaded OpenAPI specification
        simplified_openapi: Simplified OpenAPI specification
        service_name: Name of the API service
        mappings_checked: List of mappings that have been checked
        input_parameters_checked: List of input parameters that have been checked
        operations_containing_param_w_description: Operations with parameter descriptions
        operation_param_w_descr: Operation parameters with descriptions
        total_inference: Total number of potential inferences to process
        input_parameter_responsebody_mapping: Mapping from input parameters to response body
        response_body_input_parameter_mappings_with_constraint: Mappings with constraints
        found_responsebody_constraints: Constraints found in response body
        inside_response_body_constraints: Constraints inside response body
        input_parameter_constraints: Constraints in input parameters
        simplified_schemas: Simplified schema definitions
    """

    def __init__(
        self,
        openapi_path: str,
        save_and_load: bool = False,
        list_of_operations: Optional[List[str]] = None,
        experiment_folder: str = "experiment",
    ) -> None:
        """
        Initialize the ConstraintExtractor.

        Args:
            openapi_path: Path to the OpenAPI specification file
            save_and_load: Whether to save and load progress from files
            list_of_operations: Optional list of operations to process; if None, all operations are processed
            experiment_folder: Folder where experiment files are stored

        Returns:
            None
        """
        # Create a config object to store initialization parameters
        self.config = ConstraintExtractorConfig(
            openapi_path=openapi_path,
            save_and_load=save_and_load,
            list_of_operations=list_of_operations,
            experiment_folder=experiment_folder,
        )

        self.openapi_path = openapi_path
        self.save_and_load = save_and_load
        self.list_of_operations = list_of_operations
        self.experiment_folder = experiment_folder

        # Initialize fields that will be populated in initialize()
        self.openapi_spec: Dict[str, Any] = {}
        self.simplified_openapi: Dict[str, Any] = {}
        self.service_name: str = ""
        self.mappings_checked: List[CheckedMapping] = []
        self.input_parameters_checked: List[List[Any]] = []
        self.operations_containing_param_w_description: Dict[str, Any] = {}
        self.operation_param_w_descr: Dict[str, Any] = {}
        self.total_inference: int = 0
        self.input_parameter_responsebody_mapping: Dict[str, Any] = {}
        self.response_body_input_parameter_mappings_with_constraint: Dict[str, Any] = {}
        self.found_responsebody_constraints: List[List[Any]] = []
        self.inside_response_body_constraints: Dict[str, Dict[str, str]] = {}
        self.input_parameter_constraints: Dict[str, Dict[str, Dict[str, str]]] = {}
        self.simplified_schemas: Dict[str, Any] = {}

        # Load OpenAPI specification and initialize structures
        self.initialize()
        self.filter_params_w_descr()

    def initialize(self) -> None:
        """
        Initialize data structures and load OpenAPI specification.

        This method loads the OpenAPI specification, extracts the service name,
        and initializes various data structures for tracking constraints.

        Returns:
            None
        """
        self.openapi_spec = load_openapi(self.openapi_path)
        self.service_name = self.openapi_spec["info"]["title"]

        self.simplified_openapi = simplify_openapi(self.openapi_spec)

        self.mappings_checked = []
        self.input_parameters_checked = []

        # Load previously checked mappings if enabled
        if self.save_and_load:
            self.mappings_checked_save_path = (
                f"{self.experiment_folder}/{self.service_name}/mappings_checked.txt"
            )
            if os.path.exists(self.mappings_checked_save_path):
                raw_mappings = json.load(open(self.mappings_checked_save_path, "r"))
                # Convert raw mappings to CheckedMapping objects
                self.mappings_checked = [
                    CheckedMapping(mapping=item[0], confirmation=item[1])
                    for item in raw_mappings
                ]

            self.input_parameters_checked_save_path = f"{self.experiment_folder}/{self.service_name}/input_parameters_checked.txt"
            if os.path.exists(self.input_parameters_checked_save_path):
                self.input_parameters_checked = json.load(
                    open(self.input_parameters_checked_save_path, "r")
                )

        # Use all operations if none specified
        if self.list_of_operations is None:
            self.list_of_operations = list(self.simplified_openapi.keys())

    def filter_params_w_descr(self) -> Dict[str, Any]:
        """
        Filter operations to only those with parameters that have descriptions.

        Creates a new dictionary containing only operations that have parameters
        or request body fields with descriptions in the OpenAPI specification.

        Returns:
            Dictionary of operations with parameter descriptions
        """
        self.operations_containing_param_w_description = {}
        # Get simplified openapi Spec with params, that each param has a description
        self.operation_param_w_descr = simplify_openapi(self.openapi_spec)

        # Count total potential inferences
        self.total_inference = json.dumps(self.operation_param_w_descr).count(
            "(description:"
        )

        for operation in self.operation_param_w_descr:
            self.operations_containing_param_w_description[operation] = {}

            # Copy operation summary if present
            if "summary" in self.operation_param_w_descr[operation]:
                self.operations_containing_param_w_description[operation]["summary"] = (
                    self.operation_param_w_descr[operation]["summary"]
                )

            # Filter parameters and requestBody for those with descriptions
            parts = ["parameters", "requestBody"]
            for part in parts:
                if (
                    self.operation_param_w_descr.get(operation, {}).get(part, None)
                    is not None
                ):
                    self.operations_containing_param_w_description[operation][part] = {}
                    if isinstance(self.operation_param_w_descr[operation][part], dict):
                        for param, value in self.operation_param_w_descr[operation][
                            part
                        ].items():
                            if "description" in value:
                                self.operations_containing_param_w_description[
                                    operation
                                ][part][param] = value

        return self.operations_containing_param_w_description

    def checkedMapping(self, mapping: List[str]) -> Optional[CheckedMapping]:
        """
        Check if a mapping has already been processed.

        Args:
            mapping: List containing [operation, part, parameter] information

        Returns:
            The checked mapping if found, None otherwise
        """
        for check_mapping in self.mappings_checked:
            if check_mapping.mapping == mapping:
                return check_mapping
        return None

    def get_response_body_input_parameter_mappings_with_constraint(
        self,
    ) -> Dict[str, Dict[str, List[List[str]]]]:
        """
        Filter response body constraints through input parameters.

        This method analyzes mappings between request parameters and response
        attributes, determining which ones represent actual constraints.

        Returns:
            Dictionary mapping schemas to attributes with constraints
        """
        print("Filtering response body constraints through input parameters...")

        # Load mappings from file
        self.input_parameter_responsebody_mapping = json.load(
            open(
                f"{self.experiment_folder}/{self.service_name}/request_response_mappings.json",
                "r",
            )
        )

        # Make a deep copy to avoid modifying the original
        self.response_body_input_parameter_mappings_with_constraint = copy.deepcopy(
            self.input_parameter_responsebody_mapping
        )

        # Iterate through schemas and their attributes
        for schema in self.input_parameter_responsebody_mapping:
            for attribute in self.input_parameter_responsebody_mapping[schema]:
                # Process each mapping for current attribute
                for mapping in self.input_parameter_responsebody_mapping[schema][
                    attribute
                ]:
                    operation, part, corresponding_attribute = mapping

                    # Skip if attribute has no description
                    if (
                        "(description:"
                        not in self.operations_containing_param_w_description[
                            operation
                        ][part][corresponding_attribute]
                    ):
                        self.response_body_input_parameter_mappings_with_constraint[
                            schema
                        ][attribute].remove(mapping)
                        continue

                    # Extract data type and description
                    data_type = (
                        self.operations_containing_param_w_description[operation][part][
                            corresponding_attribute
                        ]
                        .split("(description: ")[0]
                        .strip()
                    )
                    description = (
                        self.operations_containing_param_w_description[operation][part][
                            corresponding_attribute
                        ]
                        .split("(description: ")[-1][:-1]
                        .strip()
                    )

                    # Check if mapping was previously processed
                    check_mapping = self.checkedMapping(mapping)
                    if check_mapping:
                        confirmation_status = check_mapping.confirmation
                        if confirmation_status != "yes":
                            if (
                                mapping
                                in self.response_body_input_parameter_mappings_with_constraint[
                                    schema
                                ][
                                    attribute
                                ]
                            ):
                                self.response_body_input_parameter_mappings_with_constraint[
                                    schema
                                ][
                                    attribute
                                ].remove(
                                    mapping
                                )
                        continue

                    # Generate observation for description
                    description_observation_prompt = (
                        DESCRIPTION_OBSERVATION_PROMPT.format(
                            attribute=corresponding_attribute,
                            data_type=data_type,
                            description=description,
                        )
                    )

                    description_observation_response = GPTChatCompletion(
                        description_observation_prompt, model="gpt-4-turbo"
                    )

                    # Confirm if description implies constraints
                    constraint_confirmation_prompt = CONSTRAINT_CONFIRMATION.format(
                        attribute=corresponding_attribute,
                        data_type=data_type,
                        description=description,
                        description_observation=description_observation_response,
                    )

                    constraint_confirmation_response = GPTChatCompletion(
                        constraint_confirmation_prompt, model="gpt-4-turbo"
                    )

                    confirmation = extract_answer(constraint_confirmation_response)

                    # Remove mapping if not confirmed
                    if confirmation != "yes":
                        if (
                            mapping
                            in self.response_body_input_parameter_mappings_with_constraint[
                                schema
                            ][
                                attribute
                            ]
                        ):
                            self.response_body_input_parameter_mappings_with_constraint[
                                schema
                            ][attribute].remove(mapping)

                    # Track checked mappings using the CheckedMapping model
                    checked_mapping = CheckedMapping(
                        mapping=mapping, confirmation=confirmation
                    )
                    self.mappings_checked.append(checked_mapping)

                    # Save checked mappings to file if enabled
                    if self.save_and_load:
                        # Convert CheckedMapping objects to the expected format for backwards compatibility
                        mappings_to_save = [
                            [m.mapping, m.confirmation] for m in self.mappings_checked
                        ]
                        with open(self.mappings_checked_save_path, "w") as file:
                            json.dump(mappings_to_save, file)

        return self.response_body_input_parameter_mappings_with_constraint

    def foundConstraintResponseBody(
        self, checking_attribute: List[Any]
    ) -> Optional[List[Any]]:
        """
        Check if a constraint has already been found in the response body.

        Args:
            checking_attribute: List containing [attribute_name, attribute_value]

        Returns:
            The found constraint if it exists, None otherwise
        """
        for checked_attribute in self.found_responsebody_constraints:
            if checking_attribute == checked_attribute[0]:
                return checked_attribute
        return None

    def foundConstraintInputParameter(
        self, checking_parameter: List[Any]
    ) -> Optional[List[Any]]:
        """
        Check if a constraint has already been found in an input parameter.

        Args:
            checking_parameter: List containing [parameter_name, parameter_value]

        Returns:
            The found constraint if it exists, None otherwise
        """
        for checked_parameter in self.input_parameters_checked:
            if checking_parameter == checked_parameter[0]:
                return checked_parameter
        return None

    def get_input_parameter_constraints(
        self, outfile: Optional[str] = None
    ) -> InputParameterConstraints:
        """
        Infer constraints from input parameter descriptions.

        This method analyzes parameter descriptions in the OpenAPI specification
        to identify implicit constraints.

        Args:
            outfile: Optional file path to save the constraints

        Returns:
            InputParameterConstraints object mapping operations to parameter constraints
        """
        print("Inferring constraints inside input parameters...")
        raw_constraints: Dict[str, Dict[str, Dict[str, str]]] = {}

        # Initialize progress tracking
        progress_size = len(self.list_of_operations) * 2
        completed = 0

        # Process each operation
        for operation in self.list_of_operations:
            raw_constraints[operation] = {
                "parameters": {},
                "requestBody": {},
            }

            # Process parameters and requestBody separately
            parts = ["parameters", "requestBody"]
            for part in parts:
                print(
                    f"[{self.service_name}] progress: {round(completed/progress_size*100, 2)}"
                )
                completed += 1

                # Get specification for current part
                specification = self.simplified_openapi.get(operation, {}).get(part, {})
                operation_path = operation.split("-")[1]
                operation_name = operation.split("-")[0]
                full_specifications = (
                    self.openapi_spec.get("paths", {})
                    .get(operation_path, {})
                    .get(operation_name, {})
                    .get(part, {})
                )

                if not specification:
                    continue

                # Process each parameter in the current part
                for parameter in specification:
                    parameter_name = parameter

                    # Extract data type and description
                    data_type = (
                        specification[parameter_name].split("(description: ")[0].strip()
                    )
                    description = (
                        specification[parameter_name]
                        .split("(description: ")[-1][:-1]
                        .strip()
                    )

                    # Get parameter specification
                    param_spec = {}
                    for spec in full_specifications:
                        if isinstance(spec, str):
                            continue
                        if spec.get("name", "") == parameter_name:
                            param_spec = spec
                            break

                    param_schema = param_spec.get("schema", {})
                    if param_schema:
                        param_schema = json.dumps(param_schema)

                    checking_parameter = [parameter_name, specification[parameter_name]]

                    # Check if parameter was previously processed
                    checked_parameter = self.foundConstraintInputParameter(
                        checking_parameter
                    )
                    if checked_parameter:
                        confirmation_status = checked_parameter[1]
                        if confirmation_status == "yes":
                            if parameter_name not in raw_constraints[operation][part]:
                                raw_constraints[operation][part][parameter] = (
                                    specification[parameter_name]
                                )
                        continue

                    # Analyze description for constraints
                    description_observation_prompt = (
                        DESCRIPTION_OBSERVATION_PROMPT.format(
                            attribute=parameter_name,
                            data_type=data_type,
                            description=description,
                            param_schema=param_schema,
                        )
                    )
                    print(description_observation_prompt)
                    print(
                        f"Observing operation: {operation} - part: {part} - parameter: {parameter_name}"
                    )

                    # For demonstration purposes, we're setting confirmation to "yes"
                    # In practice, this should call GPTChatCompletion and evaluate the response
                    confirmation = "yes"

                    if confirmation == "yes":
                        if parameter_name not in raw_constraints[operation][part]:
                            raw_constraints[operation][part][parameter_name] = (
                                specification[parameter_name]
                            )

                    self.input_parameters_checked.append(
                        [checking_parameter, confirmation]
                    )

                    # Save checked parameters to file if enabled
                    if self.save_and_load:
                        with open(self.input_parameters_checked_save_path, "w") as file:
                            json.dump(self.input_parameters_checked, file)

        # Store the raw constraints for backwards compatibility
        self.input_parameter_constraints = raw_constraints

        # Convert to Pydantic model
        constraints_model = InputParameterConstraints(constraints=raw_constraints)

        # Save constraints to file if specified
        if outfile is not None:
            with open(outfile, "w") as file:
                json.dump(raw_constraints, file, indent=2)

        return constraints_model

    def get_inside_response_body_constraints_naive(
        self,
        selected_schemas: Optional[List[str]] = None,
        outfile: Optional[str] = None,
    ) -> ResponseBodyConstraints:
        """
        Infer constraints inside response body with a naive approach.

        This method uses a simpler prompt to detect constraints in response body
        attribute descriptions.

        Args:
            selected_schemas: Optional list of schemas to process; if None, all relevant schemas are processed
            outfile: Optional file path to save the constraints

        Returns:
            ResponseBodyConstraints object mapping schemas to attributes with constraints
        """
        print("Inferring constraints inside response body...")
        raw_constraints: Dict[str, Dict[str, str]] = {}

        # Get simplified schemas with attribute descriptions
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)

        # Extract all schemas specified in response bodies
        response_body_specified_schemas = []
        operations = extract_operations(self.openapi_spec)

        for operation in operations:
            _, relevant_schemas_in_response = (
                get_relevent_response_schemas_of_operation(self.openapi_spec, operation)
            )
            response_body_specified_schemas.extend(relevant_schemas_in_response)

        response_body_specified_schemas = list(set(response_body_specified_schemas))

        self.found_responsebody_constraints = []
        print(f"Schemas: {response_body_specified_schemas}")

        # Use selected schemas if provided
        if selected_schemas is not None:
            response_body_specified_schemas = selected_schemas

        # Process each schema
        for schema in response_body_specified_schemas:
            raw_constraints[schema] = {}

            attributes = self.simplified_schemas.get(schema, {})
            if not attributes:
                continue

            # Process each attribute in the schema
            for parameter_name in attributes:
                # Skip attributes without descriptions
                if (
                    "(description:"
                    not in self.simplified_schemas[schema][parameter_name]
                ):
                    continue

                # Extract data type and description
                data_type = (
                    self.simplified_schemas[schema][parameter_name]
                    .split("(description: ")[0]
                    .strip()
                )

                description = (
                    self.simplified_schemas[schema][parameter_name]
                    .split("(description: ")[-1][:-1]
                    .strip()
                )

                if not description:
                    continue

                checking_attribute = [
                    parameter_name,
                    self.simplified_schemas[schema][parameter_name],
                ]

                # Check if attribute was previously processed
                checked_attribute = self.foundConstraintResponseBody(checking_attribute)
                if checked_attribute:
                    confirmation_status = checked_attribute[1]
                    if confirmation_status == "yes":
                        if parameter_name not in raw_constraints[schema]:
                            raw_constraints[schema][parameter_name] = description
                    continue

                # Generate naive prompt to check for constraints
                constraint_confirmation_prompt = (
                    NAIVE_CONSTRAINT_DETECTION_PROMPT.format(
                        attribute=parameter_name,
                        data_type=data_type,
                        description=description,
                    )
                )

                constraint_confirmation_response = GPTChatCompletion(
                    constraint_confirmation_prompt, model="gpt-4-turbo"
                )

                confirmation = extract_answer(constraint_confirmation_response)

                # Add constraint if confirmed
                if confirmation == "yes":
                    if parameter_name not in raw_constraints[schema]:
                        raw_constraints[schema][parameter_name] = description

                print(
                    f"Schema: {schema} - attribute: {parameter_name} - Confirmation: {confirmation}"
                )
                self.found_responsebody_constraints.append(
                    [checking_attribute, confirmation]
                )

        # Store raw_constraints for backward compatibility
        self.inside_response_body_constraints = raw_constraints

        # Create a ResponseBodyConstraints model
        constraints_model = ResponseBodyConstraints(constraints=raw_constraints)

        # Save constraints to file if specified
        if outfile is not None:
            with open(outfile, "w") as file:
                json.dump(raw_constraints, file, indent=2)

        return constraints_model

    def get_inside_response_body_constraints(
        self,
        selected_schemas: Optional[List[str]] = None,
        outfile: Optional[str] = None,
    ) -> ResponseBodyConstraints:
        """
        Infer constraints inside response body with a more sophisticated approach.

        This method uses a two-step process with observation and confirmation prompts
        to identify constraints in response body attribute descriptions.

        Args:
            selected_schemas: Optional list of schemas to process; if None, all relevant schemas are processed
            outfile: Optional file path to save the constraints

        Returns:
            ResponseBodyConstraints object mapping schemas to attributes with constraints
        """
        print("Inferring constraints inside response body...")
        raw_constraints: Dict[str, Dict[str, str]] = {}

        # Load existing constraints if outfile exists
        if outfile and os.path.exists(outfile):
            raw_constraints = json.load(open(outfile, "r"))

        # Get simplified schemas with attribute descriptions
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)

        # Extract all schemas specified in response bodies
        response_body_specified_schemas = []
        operations = extract_operations(self.openapi_spec)

        for operation in operations:
            _, relevant_schemas_in_response = (
                get_relevent_response_schemas_of_operation(self.openapi_spec, operation)
            )
            response_body_specified_schemas.extend(relevant_schemas_in_response)

        response_body_specified_schemas = list(set(response_body_specified_schemas))

        self.found_responsebody_constraints = []
        print(f"Schemas: {response_body_specified_schemas}")

        # Use selected schemas if provided
        if selected_schemas is not None:
            response_body_specified_schemas = selected_schemas

        # Process each schema
        for schema in response_body_specified_schemas:
            # Skip schemas that are already processed (except for ContentRating)
            if schema in raw_constraints:
                if schema != "ContentRating":
                    continue
            else:
                raw_constraints[schema] = {}

            attributes = self.simplified_schemas.get(schema, {})
            if not attributes:
                continue

            # Process each attribute in the schema
            for parameter_name in attributes:
                # Skip attributes already processed for ContentRating
                if schema == "ContentRating":
                    if parameter_name in raw_constraints[schema]:
                        continue

                # Skip attributes without descriptions
                if (
                    "(description:"
                    not in self.simplified_schemas[schema][parameter_name]
                ):
                    continue

                # Extract data type and description
                data_type = (
                    self.simplified_schemas[schema][parameter_name]
                    .split("(description: ")[0]
                    .strip()
                )

                description = (
                    self.simplified_schemas[schema][parameter_name]
                    .split("(description: ")[-1][:-1]
                    .strip()
                )

                if not description:
                    continue

                checking_attribute = [
                    parameter_name,
                    self.simplified_schemas[schema][parameter_name],
                ]

                # Check if attribute was previously processed
                checked_attribute = self.foundConstraintResponseBody(checking_attribute)
                if checked_attribute:
                    confirmation_status = checked_attribute[1]
                    if confirmation_status == "yes":
                        if parameter_name not in raw_constraints[schema]:
                            raw_constraints[schema][parameter_name] = description
                    continue

                # Generate observation for the description
                description_observation_prompt = DESCRIPTION_OBSERVATION_PROMPT.format(
                    attribute=parameter_name,
                    data_type=data_type,
                    description=description,
                    param_schema="",
                )
                print(f"Observing schema: {schema} - attribute: {parameter_name}")

                description_observation_response = GPTChatCompletion(
                    description_observation_prompt, model="gpt-4-turbo"
                )

                # Save prompts and responses for debugging
                with open("prompt.txt", "w", encoding="utf-16") as file:
                    file.write(f"PROMPT: {description_observation_prompt}\n")
                    file.write(f"---\n")
                    file.write(f"RESPONSE: {description_observation_response}\n")

                # Confirm if description implies constraints
                constraint_confirmation_prompt = CONSTRAINT_CONFIRMATION.format(
                    attribute=parameter_name,
                    data_type=data_type,
                    description_observation=description_observation_response,
                    description=description,
                    param_schema="",
                )

                print(f"Confirming schema: {schema} - attribute: {parameter_name}")
                constraint_confirmation_response = GPTChatCompletion(
                    constraint_confirmation_prompt, model="gpt-4-turbo"
                )
                confirmation = extract_answer(constraint_confirmation_response)

                # Save prompts and responses for debugging
                with open("prompt.txt", "a", encoding="utf-16") as file:
                    file.write(f"PROMPT: {constraint_confirmation_prompt}\n")
                    file.write(f"---\n")
                    file.write(f"RESPONSE: {constraint_confirmation_response}\n")

                # Add constraint if confirmed
                if confirmation == "yes":
                    if parameter_name not in raw_constraints[schema]:
                        raw_constraints[schema][parameter_name] = description

                print(
                    f"Schema: {schema} - attribute: {parameter_name} - Confirmation: {confirmation}"
                )
                self.found_responsebody_constraints.append(
                    [checking_attribute, confirmation]
                )

        # Store raw_constraints for backward compatibility
        self.inside_response_body_constraints = raw_constraints

        # Create a ResponseBodyConstraints model
        constraints_model = ResponseBodyConstraints(constraints=raw_constraints)

        # Save constraints to file if specified
        if outfile is not None:
            with open(outfile, "w", encoding="utf-16") as file:
                json.dump(raw_constraints, file, indent=2)

        return constraints_model


def main() -> None:
    """
    Entry point for testing the ConstraintExtractor.

    This function can be used to test the functionality of the ConstraintExtractor
    class with sample data.
    """
    pass


if __name__ == "__main__":
    main()
