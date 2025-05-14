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
