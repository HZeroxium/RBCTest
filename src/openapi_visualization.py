"""
OpenAPI Utilities Visualization

This script demonstrates the functionality of various OpenAPI utility functions
by showing inputs and outputs in a visual and structured manner.
"""

import os
import json
import yaml
from utils.openapi_utils import (
    load_openapi,
    extract_operations,
    get_operation_params,
    get_schema_params,
    get_required_fields,
    get_simplified_schema,
    get_schema_required_fields,
    get_relevant_schemas_of_operation,
    get_operations_belong_to_schemas,
    simplify_openapi,
    ruler,
    jprint,
)


# Define utility functions for better visualization
def section_header(title):
    print("\n")
    ruler()
    print(f"  {title}")
    ruler()


def subsection(title):
    print(f"\n--- {title} ---")


def print_json(data, indent=2):
    """Print JSON data with proper formatting"""
    if data:
        print(json.dumps(data, indent=indent))
    else:
        print("No data available")


# Path to your OpenAPI spec file
# Replace with your actual path or add argument parsing
spec_path = "d:/Projects/Desktop/RBCTest/RBCTest_dataset/examples/openapi.yaml"

# Check if file exists, otherwise use a sample one
if not os.path.exists(spec_path):
    print(f"Warning: {spec_path} not found. Using a sample spec instead.")
    # Create a simple sample spec for demonstration
    sample_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Sample API",
            "version": "1.0.0",
            "description": "A sample API for demonstration",
        },
        "paths": {
            "/users": {
                "get": {
                    "summary": "Get all users",
                    "operationId": "getUsers",
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "description": "Maximum number of users to return",
                            "required": False,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/UserList"}
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Create a new user",
                    "operationId": "createUser",
                    "requestBody": {
                        "description": "User object to be created",
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "User created successfully",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        }
                    },
                },
            },
            "/users/{userId}": {
                "get": {
                    "summary": "Get user by ID",
                    "operationId": "getUserById",
                    "parameters": [
                        {
                            "name": "userId",
                            "in": "path",
                            "description": "ID of the user to retrieve",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful operation",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "name", "email"],
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique identifier for the user",
                        },
                        "name": {
                            "type": "string",
                            "description": "Full name of the user",
                        },
                        "email": {
                            "type": "string",
                            "description": "Email address of the user",
                        },
                        "age": {"type": "integer", "description": "Age of the user"},
                        "address": {"$ref": "#/components/schemas/Address"},
                    },
                },
                "Address": {
                    "type": "object",
                    "properties": {
                        "street": {"type": "string", "description": "Street address"},
                        "city": {"type": "string", "description": "City name"},
                        "zipCode": {"type": "string", "description": "ZIP/Postal code"},
                    },
                },
                "UserList": {
                    "type": "object",
                    "properties": {
                        "users": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/User"},
                        },
                        "total": {
                            "type": "integer",
                            "description": "Total number of users",
                        },
                    },
                },
            }
        },
    }

    # Save sample spec to a temporary file
    temp_path = "d:/Projects/Desktop/RBCTest/examples/sample_openapi.yaml"
    os.makedirs(os.path.dirname(temp_path), exist_ok=True)
    with open(temp_path, "w") as f:
        yaml.dump(sample_spec, f)
    spec_path = temp_path

# Load the OpenAPI spec
section_header("LOADING OPENAPI SPECIFICATION")
openapi_spec = load_openapi(spec_path)

if not openapi_spec:
    print(f"Failed to load OpenAPI spec from {spec_path}")
    exit(1)

print(f"Successfully loaded OpenAPI spec: {openapi_spec.get('info', {}).get('title')}")
print(f"Version: {openapi_spec.get('info', {}).get('version')}")

# 1. Extract basic operations
section_header("1. EXTRACTING OPERATIONS")
operations = extract_operations(openapi_spec)
print(f"Found {len(operations)} operations:")
for i, op in enumerate(operations, 1):
    print(f"{i}. {op}")

# 2. Get operation parameters (default)
section_header("2. OPERATION PARAMETERS (DEFAULT)")
subsection("Example of get_operation_params()")
operation_params = get_operation_params(openapi_spec)
# Show only the first operation for brevity
if operations:
    example_op = operations[0]
    print(f"Parameters for '{example_op}':")
    jprint(operation_params[example_op])

# 3. Get operation parameters with descriptions
section_header("3. OPERATION PARAMETERS WITH DESCRIPTIONS")
subsection("Example of get_operation_params(get_description=True)")
operation_params_with_desc = get_operation_params(openapi_spec, get_description=True)
if operations:
    example_op = operations[0]
    print(f"Parameters with descriptions for '{example_op}':")
    jprint(operation_params_with_desc[example_op])

# 4. Get required fields only
section_header("4. REQUIRED FIELDS ONLY")
subsection("Example of get_required_fields()")
required_fields = get_required_fields(openapi_spec)
if operations:
    example_op = operations[0]
    print(f"Required fields for '{example_op}':")
    jprint(required_fields[example_op])

# 5. Examine a specific schema (if available)
section_header("5. SCHEMA PARAMETERS")
if "components" in openapi_spec and "schemas" in openapi_spec["components"]:
    schema_keys = list(openapi_spec["components"]["schemas"].keys())
    if schema_keys:
        example_schema_name = schema_keys[0]
        example_schema = openapi_spec["components"]["schemas"][example_schema_name]

        subsection(f"Original Schema: {example_schema_name}")
        jprint(example_schema)

        subsection(f"Parsed Schema Parameters")
        schema_params = get_schema_params(
            example_schema, openapi_spec, get_description=True
        )
        jprint(schema_params)

        subsection(f"Required Fields for Schema")
        schema_required = get_schema_required_fields(example_schema, openapi_spec)
        jprint(schema_required)

# 6. Get Simplified Schema
section_header("6. SIMPLIFIED SCHEMA")
simplified_schema = get_simplified_schema(openapi_spec)
if simplified_schema:
    subsection("Example of a simplified schema")
    # Just show one schema for brevity
    example_key = list(simplified_schema.keys())[0]
    print(f"Simplified schema for '{example_key}':")
    jprint(simplified_schema[example_key])
else:
    print("No simplified schema available")

# 7. Schema operations relationships
section_header("7. SCHEMA AND OPERATIONS RELATIONSHIPS")
operations_by_schema = get_operations_belong_to_schemas(openapi_spec)
if operations_by_schema:
    subsection("Operations by Schema")
    for schema_name, ops in operations_by_schema.items():
        print(f"\nSchema: {schema_name}")
        print("  Operations:")
        for op in ops:
            print(f"    - {op}")
else:
    print("No schema-operation relationships found")

# 8. Relevant schemas for a specific operation
section_header("8. RELEVANT SCHEMAS FOR OPERATIONS")
if operations:
    example_op = operations[0]
    main_schemas, relevant_schemas = get_relevant_schemas_of_operation(
        example_op, openapi_spec
    )

    subsection(f"Main response schemas for '{example_op}'")
    print_json(main_schemas)

    subsection(f"All relevant schemas for '{example_op}'")
    print_json(relevant_schemas)

# 9. Simplified OpenAPI spec
section_header("9. SIMPLIFIED OPENAPI SPECIFICATION")
simplified_openapi = simplify_openapi(openapi_spec)
if operations:
    example_op = operations[0]
    subsection(f"Simplified spec for '{example_op}'")
    print_json(simplified_openapi[example_op])

# Save outputs to a file (optional)
output_dir = "d:/Projects/Desktop/RBCTest/output"
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, "openapi_visualization_results.json")

output_data = {
    "api_info": {
        "title": openapi_spec.get("info", {}).get("title"),
        "version": openapi_spec.get("info", {}).get("version"),
    },
    "operations": operations,
    "operation_params_example": operation_params[operations[0]] if operations else None,
    "required_fields_example": required_fields[operations[0]] if operations else None,
    "simplified_schema_example": (
        simplified_schema[list(simplified_schema.keys())[0]]
        if simplified_schema
        else None
    ),
    "schema_operations_relationships": operations_by_schema,
}

with open(output_file, "w") as f:
    json.dump(output_data, f, indent=2)
print(f"\nResults have been saved to {output_file}")
