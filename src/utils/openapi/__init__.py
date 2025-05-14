"""
OpenAPI utilities for working with OpenAPI specifications.

This module provides functions for loading, parsing, and analyzing OpenAPI specifications.
This is the main entry point that re-exports functions from the modular implementation.
"""

# Re-export all functions from the modular implementation to maintain backward compatibility
from .openapi_core import (
    load_openapi,
    extract_operations,
    get_ref,
    find_object_with_key,
    isSuccessStatusCode,
    ruler,
    jprint,
    success_code,
    convert_path_fn,
    extract_ref_values,
)

from .openapi_schema import (
    get_schema_params,
    get_schema_required_fields,
    get_simplified_schema,
    get_schema_recursive,
    list_all_param_names,
)

from .openapi_operations import (
    get_operation_params,
    get_required_fields,
    contains_required_parameters,
    get_relevant_schemas_of_operation,
    get_operations_belong_to_schemas,
    add_test_object_to_openapi,
    get_test_object_path,
    filter_params_has_description,
    get_operation_id,
    get_response_body_name_and_type,
    get_relevent_response_schemas_of_operation,
    get_main_response_schemas_of_operation,
    get_relevant_schema_of_operation,
    simplify_openapi,
)

# For backward compatibility, import all the necessary libraries here
import copy
import json
import yaml
import re
import os
