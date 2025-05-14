# /src/response_body_verification/parameter_responsebody_mapping.py

"""
Parameter-Response Body Mapping Module

This module provides functionality to map request parameters to response body attributes
in OpenAPI specifications. It identifies relationships between input parameters and
response fields to detect constraints that may exist between them.

The main class, ParameterResponseMapper, analyzes OpenAPI specifications to find
mappings between request parameters and response body attributes that represent
the same semantic concept, which can indicate potential constraints.
"""

import os
import json
import copy
from typing import Dict, List, Optional, Any


from utils.openapi_utils import (
    load_openapi,
    get_simplified_schema,
    simplify_openapi,
    get_relevant_schemas_of_operation,
)
from utils.llm_utils import llm_chat_completion
from utils.text_extraction import extract_answer, extract_coresponding_attribute
from utils.schema_utils import (
    standardize_string,
    get_data_type,
    filter_attributes_in_schema_by_data_type,
    verify_attribute_in_schema,
    find_common_fields,
)
from constant import (
    PARAMETER_OBSERVATION,
    SCHEMA_OBSERVATION,
    PARAMETER_SCHEMA_MAPPING_PROMPT,
    NAIVE_PARAMETER_SCHEMA_MAPPING_PROMPT,
    MAPPING_CONFIRMATION,
)
from models.mapping_models import (
    FoundMapping,
    SchemaMapping,
    ParameterResponseMapperConfig,
)


class ParameterResponseMapper:
    """
    Maps input parameters to response body attributes in OpenAPI specifications.

    This class analyzes an OpenAPI specification to identify relationships between
    input parameters and response body attributes, which can indicate potential
    constraints that should be verified during testing.

    The mapping process involves:
    1. Loading and analyzing the OpenAPI specification
    2. Identifying parameters with descriptions
    3. Finding potential mappings between input parameters and response attributes
    4. Validating the mappings using LLM-based analysis

    Attributes:
        config: Configuration for the mapping process
        openapi_spec: Loaded OpenAPI specification
        simplified_schemas: Simplified schema definitions from the OpenAPI spec
        simplified_openapi: Simplified operations from the OpenAPI spec
        service_name: Name of the API service
        input_parameter_constraints: Constraints on input parameters
        inside_response_body_constraints: Constraints inside response bodies
        found_mappings: List of mappings already found
        list_of_schemas: List of schemas to process
        operations_containing_param_w_description: Operations with parameter descriptions
        operation_param_w_descr: Operation parameters with descriptions
        response_body_input_parameter_mappings: Generated mappings
    """

    def __init__(
        self,
        openapi_path: str,
        except_attributes_found_constraints_inside_response_body: bool = False,
        save_and_load: bool = False,
        list_of_available_schemas: Optional[List[str]] = None,
        outfile: Optional[str] = None,
        experiment_folder: str = "experiment_our",
        is_naive: bool = False,
    ) -> None:
        """
        Initialize the ParameterResponseMapper.

        Args:
            openapi_path: Path to the OpenAPI specification file
            except_attributes_found_constraints_inside_response_body: Whether to exclude attributes that have constraints inside response body
            save_and_load: Whether to save and load progress from files
            list_of_available_schemas: Optional list of schemas to process; if None, all schemas are processed
            outfile: Path to the output file for saving results
            experiment_folder: Folder where experiment files are stored
            is_naive: Whether to use the naive mapping approach

        Returns:
            None
        """
        # Create a config object to store initialization parameters
        self.config = ParameterResponseMapperConfig(
            openapi_path=openapi_path,
            except_attributes_found_constraints_inside_response_body=except_attributes_found_constraints_inside_response_body,
            save_and_load=save_and_load,
            list_of_available_schemas=list_of_available_schemas,
            outfile=outfile,
            experiment_folder=experiment_folder,
            is_naive=is_naive,
        )

        # Store configuration parameters as instance variables for backward compatibility
        self.openapi_spec = load_openapi(openapi_path)
        self.except_attributes_found_constraints = (
            except_attributes_found_constraints_inside_response_body
        )
        self.save_and_load = save_and_load
        self.list_of_available_schemas = list_of_available_schemas
        self.outfile = outfile
        self.experiment_folder = experiment_folder

        # Initialize data structures
        self.initialize()
        self.filter_params_w_descr()

        # Perform mapping based on configuration
        if is_naive:
            self.mapping_response_bodies_to_input_parameters_naive()
        else:
            self.mapping_response_bodies_to_input_parameters()

    def initialize(self) -> None:
        """
        Initialize data structures and load required data.

        This method loads the OpenAPI specification, extracts the service name,
        loads constraints from files, and initializes tracking structures for mappings.

        Returns:
            None
        """
        self.service_name = self.openapi_spec["info"]["title"]
        self.simplified_schemas = get_simplified_schema(self.openapi_spec)
        self.simplified_openapi = simplify_openapi(self.openapi_spec)

        # Load input parameter constraints
        self.input_parameter_constraints = json.load(
            open(
                f"{self.experiment_folder}/{self.service_name}/input_parameter.json",
                "r",
            )
        )

        # Load response body constraints if needed
        if self.except_attributes_found_constraints:
            self.inside_response_body_constraints = json.load(
                open(
                    f"{self.experiment_folder}/{self.service_name}/response_property_constraints.json",
                    "r",
                )
            )

        # Initialize found mappings
        self.found_mappings: List[FoundMapping] = []
        if self.save_and_load:
            self.save_path = (
                f"{self.experiment_folder}/{self.service_name}/found_maping.txt"
            )
            if os.path.exists(self.save_path):
                raw_mappings = json.load(open(self.save_path, "r"))
                self.found_mappings = [FoundMapping.from_list(m) for m in raw_mappings]

        # Get list of schemas to process
        self.list_of_schemas = list(self.simplified_schemas.keys())
        if self.list_of_available_schemas:
            self.list_of_schemas = self.list_of_available_schemas

    def filter_params_w_descr(self) -> Dict[str, Dict[str, Any]]:
        """
        Filter parameters to only include those with descriptions.

        Creates a new dictionary containing only operations that have parameters
        with descriptions in the OpenAPI specification.

        Returns:
            Dictionary mapping operations to their parameters with descriptions
        """
        self.operations_containing_param_w_description: Dict[str, Dict[str, Any]] = {}
        # Get simplified openapi Spec with params, that each param has a description
        self.operation_param_w_descr = simplify_openapi(self.openapi_spec)

        for operation in self.operation_param_w_descr:
            self.operations_containing_param_w_description[operation] = {}
            if "summary" in self.operation_param_w_descr[operation]:
                self.operations_containing_param_w_description[operation]["summary"] = (
                    self.operation_param_w_descr[operation]["summary"]
                )

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
                            if "(description:" in value:
                                self.operations_containing_param_w_description[
                                    operation
                                ][part][param] = value

        return self.operations_containing_param_w_description

    def foundMapping(
        self, input_parameter: str, description: str, schema: str
    ) -> Optional[FoundMapping]:
        """
        Check if a mapping has already been found.

        Args:
            input_parameter: Name of the input parameter
            description: Description of the input parameter
            schema: Name of the schema

        Returns:
            The found mapping if it exists, None otherwise
        """
        for mapping in self.found_mappings:
            if (
                mapping.parameter_name == input_parameter
                and mapping.parameter_description == description
                and mapping.schema_name == schema
            ):
                return mapping
        return None

    def exclude_attributes_found_constraint(self, schema: str) -> Dict[str, Any]:
        """
        Exclude attributes that have found constraints in a schema.

        Args:
            schema: Name of the schema to filter

        Returns:
            Dictionary containing only attributes without found constraints
        """
        return {
            key: value
            for key, value in self.simplified_schemas[schema].items()
            if key not in self.inside_response_body_constraints.get(schema, {})
        }

    def mapping_response_bodies_to_input_parameters(self) -> None:
        """
        Map input parameters to response body attributes.

        This method analyzes input parameters and response body attributes to find
        potential mappings between them that could indicate constraints.

        It uses a sophisticated approach with LLM-based analysis of parameter
        and schema descriptions to find semantically related fields.

        Returns:
            None
        """
        print(f"\nMapping input parameters to response schemas...")
        self.response_body_input_parameter_mappings: Dict[
            str, Dict[str, List[List[str]]]
        ] = {}

        progress_size = (
            2 * len(self.input_parameter_constraints) * len(self.list_of_schemas)
        )
        completed = 0

        # Process each operation with constraints
        for operation in self.input_parameter_constraints:
            operation_method, operation_path = operation.split("-", 1)
            full_operation_spec = (
                self.openapi_spec.get("paths", {})
                .get(operation_path, {})
                .get(operation_method, {})
            )

            if not full_operation_spec:
                continue

            # Get main response schemas for the operation
            main_repsonse_schemas, _ = get_relevant_schemas_of_operation(
                operation, self.openapi_spec
            )
            print(
                f"Operation: {operation}, Main response schemas: {main_repsonse_schemas}"
            )

            # Process each response schema
            for schema in main_repsonse_schemas:
                for part in ["parameters", "requestBody"]:
                    try:
                        print(
                            f"[{self.service_name}] progress: {round(completed/progress_size*100, 2)}"
                        )
                        completed += 1

                        specification = self.input_parameter_constraints.get(
                            operation, {}
                        ).get(part, {})
                        if not specification:
                            continue

                        if schema not in self.simplified_schemas:
                            continue

                        schema_spec = self.simplified_schemas[schema]

                        # Process each parameter in the specification
                        for param in specification:
                            print(f"Mapping {param} from {operation} to {schema}")
                            description = (
                                specification[param]
                                .split("(description:")[-1][:-1]
                                .strip()
                            )

                            # Check if mapping already exists
                            found_mapping = self.foundMapping(
                                param, description, schema
                            )

                            if found_mapping:
                                found_corresponding_attribute = (
                                    found_mapping.corresponding_attribute
                                )
                                if found_corresponding_attribute is None:
                                    continue

                                # Add to mappings dictionary
                                if (
                                    schema
                                    not in self.response_body_input_parameter_mappings
                                ):
                                    self.response_body_input_parameter_mappings[
                                        schema
                                    ] = {
                                        found_corresponding_attribute: [
                                            [operation, part, param]
                                        ]
                                    }
                                elif (
                                    found_corresponding_attribute
                                    not in self.response_body_input_parameter_mappings[
                                        schema
                                    ]
                                ):
                                    self.response_body_input_parameter_mappings[schema][
                                        found_corresponding_attribute
                                    ] = [[operation, part, param]]
                                else:
                                    self.response_body_input_parameter_mappings[schema][
                                        found_corresponding_attribute
                                    ].append([operation, part, param])
                                continue

                            # Save progress if enabled
                            if self.save_and_load:
                                with open(self.save_path, "w") as file:
                                    json.dump(
                                        [m.to_list() for m in self.found_mappings], file
                                    )

                            # Create new mapping
                            mapping = FoundMapping(
                                parameter_name=param,
                                parameter_description=description,
                                schema_name=schema,
                                corresponding_attribute=None,
                            )

                            # Filter attributes by data type
                            filtering_data_type = get_data_type(specification[param])
                            filtered_attr_schema = (
                                filter_attributes_in_schema_by_data_type(
                                    schema_spec, filtering_data_type
                                )
                            )

                            if not filtered_attr_schema:
                                self.found_mappings.append(mapping)
                                continue

                            # Extract method and endpoint for prompts
                            method = operation.split("-")[0]
                            endpoint = "-".join(operation.split("-")[1:])
                            print(
                                f"Mapping {param} to {json.dumps(filtered_attr_schema)} in {schema}"
                            )

                            # Generate parameter observation prompt
                            parameter_observation_prompt = PARAMETER_OBSERVATION.format(
                                method=method.upper(),
                                endpoint=endpoint,
                                attribute=param,
                                description=description,
                            )

                            parameter_observation_response = llm_chat_completion(
                                parameter_observation_prompt, model="gpt-4-turbo"
                            )

                            # Generate schema observation prompt
                            schema_observation_prompt = SCHEMA_OBSERVATION.format(
                                schema=schema,
                                specification=json.dumps(filtered_attr_schema),
                            )

                            schema_observation_response = llm_chat_completion(
                                schema_observation_prompt, model="gpt-4-turbo"
                            )

                            # Generate mapping prompt
                            mapping_attribute_to_schema_prompt = PARAMETER_SCHEMA_MAPPING_PROMPT.format(
                                method=method.upper(),
                                endpoint=endpoint,
                                attribute=param,
                                description=description,
                                parameter_observation=parameter_observation_response,
                                schema=schema,
                                schema_observation=schema_observation_response,
                                attributes=[attr for attr in filtered_attr_schema],
                            )

                            mapping_attribute_to_schema_response = llm_chat_completion(
                                mapping_attribute_to_schema_prompt, model="gpt-4-turbo"
                            )

                            print("GPT: ", mapping_attribute_to_schema_response)

                            # Extract answer from response
                            answer = extract_answer(
                                mapping_attribute_to_schema_response
                            )
                            if not "yes" in answer:
                                self.found_mappings.append(mapping)
                                continue

                            # Extract corresponding attribute from response
                            corresponding_attribute = extract_coresponding_attribute(
                                mapping_attribute_to_schema_response
                            )

                            # Verify attribute exists in schema
                            if not verify_attribute_in_schema(
                                filtered_attr_schema, corresponding_attribute
                            ):
                                self.found_mappings.append(mapping)
                                continue

                            # Generate confirmation prompt
                            mapping_confirmation_prompt = MAPPING_CONFIRMATION.format(
                                method=method.upper(),
                                endpoint=endpoint,
                                parameter_name=param,
                                description=description,
                                schema=schema,
                                corresponding_attribute=corresponding_attribute,
                            )

                            mapping_confirmation_response = llm_chat_completion(
                                mapping_confirmation_prompt, model="gpt-4-turbo"
                            )
                            mapping_status = extract_answer(
                                mapping_confirmation_response
                            )

                            # Check confirmation status
                            if "incorrect" in mapping_status:
                                print(
                                    f"[INCORRECT] {method.upper()} {endpoint} {param} --- {schema} {corresponding_attribute}"
                                )
                                self.found_mappings.append(mapping)
                                continue

                            print(
                                f"[CORRECT] {method.upper()} {endpoint} {param} --- {schema} {corresponding_attribute}"
                            )

                            # Add confirmed mapping to results
                            if (
                                schema
                                not in self.response_body_input_parameter_mappings
                            ):
                                self.response_body_input_parameter_mappings[schema] = {
                                    corresponding_attribute: [[operation, part, param]]
                                }
                            elif (
                                corresponding_attribute
                                not in self.response_body_input_parameter_mappings[
                                    schema
                                ]
                            ):
                                self.response_body_input_parameter_mappings[schema][
                                    corresponding_attribute
                                ] = [[operation, part, param]]
                            else:
                                self.response_body_input_parameter_mappings[schema][
                                    corresponding_attribute
                                ].append([operation, part, param])

                            # Update mapping and save
                            mapping.corresponding_attribute = corresponding_attribute
                            self.found_mappings.append(mapping)

                            if self.save_and_load:
                                with open(self.save_path, "w") as file:
                                    json.dump(
                                        [m.to_list() for m in self.found_mappings], file
                                    )

                            # Save results to output file if specified
                            if self.outfile:
                                with open(self.outfile, "w") as f:
                                    json.dump(
                                        self.response_body_input_parameter_mappings,
                                        f,
                                        indent=2,
                                    )
                    except Exception as e:
                        print(f"Error: {e}")
                        continue

    def mapping_response_bodies_to_input_parameters_naive(self) -> None:
        """
        Map input parameters to response body attributes using a naive approach.

        This method is a simplified version of the mapping process that uses less
        sophisticated prompts and analysis, which can be faster but potentially
        less accurate.

        Returns:
            None
        """
        print(f"\nNAIVE Mapping input parameters to response schemas...")
        self.response_body_input_parameter_mappings: Dict[
            str, Dict[str, List[List[str]]]
        ] = {}

        progress_size = (
            2 * len(self.input_parameter_constraints) * len(self.list_of_schemas)
        )
        completed = 0

        # Process each operation with constraints
        for operation in self.input_parameter_constraints:
            operation_path = operation.split("-")[1]
            operation_method = operation.split("-")[0]
            full_operation_spec = (
                self.openapi_spec.get("paths", {})
                .get(operation_path, {})
                .get(operation_method, {})
            )

            if not full_operation_spec:
                continue

            # Get main response schemas for the operation
            main_repsonse_schemas, _ = get_relevant_schemas_of_operation(
                operation, self.openapi_spec
            )
            print(
                f"Operation: {operation}, Main response schemas: {main_repsonse_schemas}"
            )

            # Process each response schema
            for schema in main_repsonse_schemas:
                for part in ["parameters", "requestBody"]:
                    try:
                        print(
                            f"[{self.service_name}] progress: {round(completed/progress_size*100, 2)}"
                        )
                        completed += 1

                        specification = self.input_parameter_constraints.get(
                            operation, {}
                        ).get(part, {})
                        if not specification:
                            continue

                        if schema not in self.simplified_schemas:
                            continue

                        schema_spec = self.simplified_schemas[schema]

                        # Process each parameter in the specification
                        for param in specification:
                            print(f"Mapping {param} from {operation} to {schema}")
                            description = (
                                specification[param]
                                .split("(description:")[-1][:-1]
                                .strip()
                            )

                            # Check if mapping already exists
                            found_mapping = self.foundMapping(
                                param, description, schema
                            )

                            if found_mapping:
                                found_corresponding_attribute = (
                                    found_mapping.corresponding_attribute
                                )
                                if found_corresponding_attribute is None:
                                    continue

                                # Add to mappings dictionary
                                if (
                                    schema
                                    not in self.response_body_input_parameter_mappings
                                ):
                                    self.response_body_input_parameter_mappings[
                                        schema
                                    ] = {
                                        found_corresponding_attribute: [
                                            [operation, part, param]
                                        ]
                                    }
                                elif (
                                    found_corresponding_attribute
                                    not in self.response_body_input_parameter_mappings[
                                        schema
                                    ]
                                ):
                                    self.response_body_input_parameter_mappings[schema][
                                        found_corresponding_attribute
                                    ] = [[operation, part, param]]
                                else:
                                    self.response_body_input_parameter_mappings[schema][
                                        found_corresponding_attribute
                                    ].append([operation, part, param])
                                continue

                            # Save progress if enabled
                            if self.save_and_load:
                                with open(self.save_path, "w") as file:
                                    json.dump(
                                        [m.to_list() for m in self.found_mappings], file
                                    )

                            # Create new mapping
                            mapping = FoundMapping(
                                parameter_name=param,
                                parameter_description=description,
                                schema_name=schema,
                                corresponding_attribute=None,
                            )

                            # Filter attributes by data type
                            filtering_data_type = get_data_type(specification[param])
                            filtered_attr_schema = (
                                filter_attributes_in_schema_by_data_type(
                                    schema_spec, filtering_data_type
                                )
                            )

                            if not filtered_attr_schema:
                                self.found_mappings.append(mapping)
                                continue

                            # Extract method and endpoint for prompts
                            method = operation.split("-")[0]
                            endpoint = "-".join(operation.split("-")[1:])
                            print(
                                f"Mapping {param} to {json.dumps(filtered_attr_schema)} in {schema}"
                            )

                            # Generate naive mapping prompt (simplified approach)
                            mapping_attribute_to_schema_prompt = (
                                NAIVE_PARAMETER_SCHEMA_MAPPING_PROMPT.format(
                                    method=method.upper(),
                                    endpoint=endpoint,
                                    attribute=param,
                                    description=description,
                                    schema_specification=json.dumps(
                                        filtered_attr_schema
                                    ),
                                    schema=schema,
                                    attributes=[attr for attr in filtered_attr_schema],
                                )
                            )

                            mapping_attribute_to_schema_response = llm_chat_completion(
                                mapping_attribute_to_schema_prompt, model="gpt-4-turbo"
                            )

                            print("GPT: ", mapping_attribute_to_schema_response)

                            # Extract answer from response
                            answer = extract_answer(
                                mapping_attribute_to_schema_response
                            )
                            if not "yes" in answer:
                                self.found_mappings.append(mapping)
                                continue

                            # Extract corresponding attribute from response
                            corresponding_attribute = extract_coresponding_attribute(
                                mapping_attribute_to_schema_response
                            )

                            # Add mapping to results (no confirmation step in naive approach)
                            if (
                                schema
                                not in self.response_body_input_parameter_mappings
                            ):
                                self.response_body_input_parameter_mappings[schema] = {
                                    corresponding_attribute: [[operation, part, param]]
                                }
                            elif (
                                corresponding_attribute
                                not in self.response_body_input_parameter_mappings[
                                    schema
                                ]
                            ):
                                self.response_body_input_parameter_mappings[schema][
                                    corresponding_attribute
                                ] = [[operation, part, param]]
                            else:
                                self.response_body_input_parameter_mappings[schema][
                                    corresponding_attribute
                                ].append([operation, part, param])

                            # Update mapping and save
                            mapping.corresponding_attribute = corresponding_attribute
                            self.found_mappings.append(mapping)

                            if self.save_and_load:
                                with open(self.save_path, "w") as file:
                                    json.dump(
                                        [m.to_list() for m in self.found_mappings], file
                                    )

                    except Exception as e:
                        print(f"Error: {e}")
                        continue

    def get_mappings(self) -> Dict[str, Dict[str, List[List[str]]]]:
        """
        Get the generated mappings between input parameters and response attributes.

        Returns:
            Dictionary mapping schemas to attributes and their parameter mappings
        """
        return self.response_body_input_parameter_mappings

    def export_mappings(self, output_path: Optional[str] = None) -> None:
        """
        Export the generated mappings to a JSON file.

        Args:
            output_path: Path to the output file (uses self.outfile if None)

        Returns:
            None
        """
        file_path = output_path or self.outfile
        if not file_path:
            raise ValueError("No output path specified")

        with open(file_path, "w") as f:
            json.dump(self.response_body_input_parameter_mappings, f, indent=2)
