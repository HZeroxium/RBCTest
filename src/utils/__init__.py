"""
Utilities package for the RBCTest project.

This package contains various utility modules for working with OpenAPI specifications
and other common tasks.
"""

# Import key functions for easy access at the package level
from .openapi_utils import (
    load_openapi,
    extract_operations,
    get_operation_params,
    get_schema_params,
    get_required_fields,
    get_simplified_schema,
    simplify_openapi,
)

# Import text extraction utilities
from .text_extraction import (
    extract_variables,
    extract_values,
    extract_dict_attributes,
    extract_python_code,
    extract_answer,
    extract_summary_constraint,
    extract_idl,
    extract_coresponding_attribute,
    is_construct_json_object,
    standardize_returned_idl,
    extract_structured_field,
)

# Import schema utilities
from .schema_utils import (
    standardize_string,
    get_data_type,
    filter_attributes_in_schema_by_data_type,
    verify_attribute_in_schema,
    find_common_fields,
)
