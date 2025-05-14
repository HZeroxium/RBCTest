# /src/utils/excel_utils.py

"""
Excel Utility Functions Module

This module provides functions for converting between various data formats
and Excel files, with robust error handling and validation.
"""

import os
import json
from typing import Dict, Any, Union, Optional, List, Tuple
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field, field_validator


class JsonToExcelConversionInput(BaseModel):
    """Input parameters for JSON to Excel conversion."""

    json_file: str = Field(
        ..., description="Path to the JSON file to be converted to Excel"
    )
    excel_file: str = Field(..., description="Path where the Excel file will be saved")
    sheet_name: str = Field(
        "Sheet1", description="Name of the sheet where data will be saved"
    )
    include_index: bool = Field(
        False, description="Whether to include DataFrame index in the Excel output"
    )

    @field_validator("json_file")
    def json_file_must_exist(cls, v):
        if not os.path.exists(v):
            raise ValueError(f"JSON file not found: {v}")
        return v

    @field_validator("excel_file")
    def ensure_excel_directory_exists(cls, v):
        directory = os.path.dirname(v)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Cannot create directory for Excel file: {e}")
        return v


class JsonToExcelConversionResult(BaseModel):
    """Result of a JSON to Excel conversion operation."""

    success: bool = Field(..., description="Whether the conversion was successful")
    message: str = Field(..., description="Description of the result or error message")
    excel_file: Optional[str] = Field(
        None, description="Path to the created Excel file if successful"
    )
    rows_processed: Optional[int] = Field(
        None, description="Number of rows processed during conversion"
    )
    columns_processed: Optional[int] = Field(
        None, description="Number of columns processed during conversion"
    )


class DataFrameToExcelInput(BaseModel):
    """Input parameters for DataFrame to Excel conversion."""

    excel_file: str = Field(..., description="Path where the Excel file will be saved")
    sheet_name: str = Field(
        "Sheet1", description="Name of the sheet where data will be saved"
    )
    include_index: bool = Field(
        False, description="Whether to include DataFrame index in the Excel output"
    )

    @field_validator("excel_file")
    def ensure_excel_directory_exists(cls, v):
        directory = os.path.dirname(v)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
            except Exception as e:
                raise ValueError(f"Cannot create directory for Excel file: {e}")
        return v


def convert_json_to_excel(
    json_file: str,
    excel_file: str,
    sheet_name: str = "Sheet1",
    include_index: bool = False,
) -> None:
    """
    Convert a JSON file to an Excel file.

    This function reads data from a JSON file and writes it to an Excel file.
    The JSON structure should be convertible to a pandas DataFrame.

    Args:
        json_file: Path to the JSON file to read data from
        excel_file: Path to the Excel file where data will be saved
        sheet_name: Name of the sheet in the Excel file (default: "Sheet1")
        include_index: Whether to include DataFrame index in the Excel output (default: False)

    Returns:
        None

    Raises:
        FileNotFoundError: If the JSON file doesn't exist
        ValueError: If the JSON data cannot be converted to a DataFrame
        IOError: If there's an error writing the Excel file
    """
    try:
        # Read the JSON file
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Convert the JSON data to a DataFrame
        df = pd.DataFrame(data)

        # Create directory for Excel file if it doesn't exist
        excel_dir = os.path.dirname(excel_file)
        if excel_dir and not os.path.exists(excel_dir):
            os.makedirs(excel_dir, exist_ok=True)

        # Write the DataFrame to an Excel file
        df.to_excel(excel_file, sheet_name=sheet_name, index=include_index)

    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file not found: {json_file}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in file: {json_file}")
    except Exception as e:
        raise IOError(f"Error converting JSON to Excel: {str(e)}")


def convert_json_to_excel_validated(
    input_data: Union[JsonToExcelConversionInput, Dict[str, Any]],
) -> JsonToExcelConversionResult:
    """
    Convert a JSON file to an Excel file with input validation and detailed result reporting.

    This function is a wrapper around convert_json_to_excel that adds input validation
    with Pydantic models and provides a structured result object.

    Args:
        input_data: Either a JsonToExcelConversionInput model or a dictionary with the same fields

    Returns:
        JsonToExcelConversionResult: Object containing success status, message, and statistics

    Example:
        >>> result = convert_json_to_excel_validated({
        ...     "json_file": "data.json",
        ...     "excel_file": "output.xlsx",
        ...     "sheet_name": "DataSheet"
        ... })
        >>> print(result.success, result.message)
    """
    # Convert dictionary to Pydantic model if needed
    if isinstance(input_data, dict):
        try:
            input_data = JsonToExcelConversionInput(**input_data)
        except Exception as e:
            return JsonToExcelConversionResult(
                success=False, message=f"Invalid input data: {str(e)}", excel_file=None
            )

    try:
        # Read the JSON file to get stats before conversion
        with open(input_data.json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        df = pd.DataFrame(data)
        rows = df.shape[0]
        cols = df.shape[1]

        # Perform the conversion
        convert_json_to_excel(
            input_data.json_file,
            input_data.excel_file,
            input_data.sheet_name,
            input_data.include_index,
        )

        return JsonToExcelConversionResult(
            success=True,
            message=f"Successfully converted {input_data.json_file} to {input_data.excel_file}",
            excel_file=input_data.excel_file,
            rows_processed=rows,
            columns_processed=cols,
        )

    except Exception as e:
        return JsonToExcelConversionResult(
            success=False, message=f"Error during conversion: {str(e)}", excel_file=None
        )


def convert_dataframe_to_excel(
    df: pd.DataFrame, output_config: Union[DataFrameToExcelInput, Dict[str, Any]]
) -> JsonToExcelConversionResult:
    """
    Convert a pandas DataFrame to an Excel file.

    This function takes an in-memory DataFrame and writes it to an Excel file
    based on the provided configuration.

    Args:
        df: The pandas DataFrame to convert to Excel
        output_config: Either a DataFrameToExcelInput model or a dictionary with the same fields

    Returns:
        JsonToExcelConversionResult: Object containing success status and message

    Example:
        >>> df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        >>> result = convert_dataframe_to_excel(df, {
        ...     "excel_file": "output.xlsx",
        ...     "sheet_name": "Data"
        ... })
        >>> print(result.success)
    """
    # Convert dictionary to Pydantic model if needed
    if isinstance(output_config, dict):
        try:
            output_config = DataFrameToExcelInput(**output_config)
        except Exception as e:
            return JsonToExcelConversionResult(
                success=False,
                message=f"Invalid output configuration: {str(e)}",
                excel_file=None,
            )

    try:
        # Create directory for Excel file if it doesn't exist
        excel_dir = os.path.dirname(output_config.excel_file)
        if excel_dir and not os.path.exists(excel_dir):
            os.makedirs(excel_dir, exist_ok=True)

        # Write the DataFrame to an Excel file
        df.to_excel(
            output_config.excel_file,
            sheet_name=output_config.sheet_name,
            index=output_config.include_index,
        )

        return JsonToExcelConversionResult(
            success=True,
            message=f"Successfully saved DataFrame to {output_config.excel_file}",
            excel_file=output_config.excel_file,
            rows_processed=df.shape[0],
            columns_processed=df.shape[1],
        )

    except Exception as e:
        return JsonToExcelConversionResult(
            success=False,
            message=f"Error saving DataFrame to Excel: {str(e)}",
            excel_file=None,
        )


def excel_to_dataframe(
    excel_file: str,
    sheet_name: Optional[Union[str, int]] = 0,
    header: Optional[int] = 0,
    usecols: Optional[Union[List[int], str]] = None,
) -> Tuple[Optional[pd.DataFrame], str]:
    """
    Convert an Excel file to a pandas DataFrame.

    Args:
        excel_file: Path to the Excel file to read
        sheet_name: Name or index of the sheet to read (default: first sheet)
        header: Row to use as column names (0-indexed, default: 0)
        usecols: Columns to read (default: all columns)

    Returns:
        Tuple containing:
            - The pandas DataFrame if successful, None otherwise
            - Status message describing the result or error

    Example:
        >>> df, message = excel_to_dataframe("data.xlsx", sheet_name="Sheet1")
        >>> if df is not None:
        ...     print(f"Loaded {df.shape[0]} rows with message: {message}")
        ... else:
        ...     print(f"Error: {message}")
    """
    try:
        if not os.path.exists(excel_file):
            return None, f"Excel file not found: {excel_file}"

        df = pd.read_excel(
            excel_file, sheet_name=sheet_name, header=header, usecols=usecols
        )

        return (
            df,
            f"Successfully read Excel file with {df.shape[0]} rows and {df.shape[1]} columns",
        )

    except Exception as e:
        return None, f"Error reading Excel file: {str(e)}"


def convert_json_to_excel_response_property_constraints(
    json_file: str, openapi_spec_file: str, output_file: str
) -> None:
    """
    Convert JSON response property constraints to an Excel file.

    Args:
        json_file: Path to the JSON file containing response property constraints
        openapi_spec_file: Path to the OpenAPI specification file
        output_file: Path where the Excel file will be saved

    Returns:
        None
    """
    if not os.path.exists(json_file) or not os.path.exists(openapi_spec_file):
        print(f"File {json_file} does not exist")
        return

    openapi_spec = json.load(open(openapi_spec_file, "r", encoding="utf-8-sig"))
    simplified_openapi = simplify_openapi(openapi_spec)
    simplified_schemas = get_simplified_schema(openapi_spec)

    service_name = openapi_spec["info"]["title"]

    # Load selected operations and schemas if available
    try:
        selected_operations = open(
            "src/stripe_selected/selected_operations.txt", "r"
        ).readlines()
        selected_operations = [operation.strip() for operation in selected_operations]
    except:
        selected_operations = []

    try:
        selected_schemas = open(
            "src/stripe_selected/selected_schemas.txt", "r"
        ).readlines()
        selected_schemas = [schema.strip() for schema in selected_schemas]
    except:
        selected_schemas = []

    inside_response_body_constraints = json.load(open(json_file, "r"))

    data = []
    no_of_constraints = 0
    operations_with_constraint = set()

    for operation in simplified_openapi:
        if service_name == "StripeClone API" and operation not in selected_operations:
            continue
        _, relevant_schemas = get_relevent_response_schemas_of_operation(
            openapi_spec, operation
        )

        for schema in relevant_schemas:
            if service_name == "StripeClone API" and schema not in selected_schemas:
                continue
            attributes_with_constraint = inside_response_body_constraints.get(
                schema, {}
            )

            for attribute in attributes_with_constraint:
                data.append(
                    {
                        "operation": operation,
                        "response resource": schema,
                        "attribute": attribute,
                        "description": attributes_with_constraint[attribute],
                    }
                )
                no_of_constraints += 1
                operations_with_constraint.add(operation)

    # Remove duplicates and keep the first occurrence
    data = [dict(t) for t in {tuple(d.items()) for d in data}]
    if not data:
        data = [
            {
                "operation": "",
                "response resource": "",
                "attribute": "",
                "description": "",
            }
        ]

    df = pd.DataFrame(data)
    df.to_excel(f"{output_file}", index=False)
    print(f"Converted to {output_file}")
    print(f"No. of constraints in response bodies: {no_of_constraints}")
    print(
        f"No. of operation having constraints inside response body: {len(operations_with_constraint)}"
    )


def convert_json_to_excel_request_response_constraints(
    json_file: str, openapi_spec_file: str, output_file: str
) -> None:
    """
    Convert JSON request-response constraints to an Excel file.

    Args:
        json_file: Path to the JSON file containing request-response constraints
        openapi_spec_file: Path to the OpenAPI specification file
        output_file: Path where the Excel file will be saved

    Returns:
        None
    """
    if not os.path.exists(json_file) or not os.path.exists(openapi_spec_file):
        print(f"File {json_file} does not exist")
        return

    openapi_spec = json.load(open(openapi_spec_file, "r", encoding="utf-8"))
    simplified_openapi = simplify_openapi(openapi_spec)
    simplified_schemas = get_simplified_schema(openapi_spec)

    try:
        selected_operations = open(
            "src/stripe_selected/selected_operations.txt", "r"
        ).readlines()
        selected_operations = [operation.strip() for operation in selected_operations]
    except:
        selected_operations = []

    service_name = openapi_spec["info"]["title"]
    response_body_input_parameter_mappings_with_constraint = json.load(
        open(json_file, "r")
    )

    data = []
    operations_with_constraint = set()

    for operation in simplified_openapi:
        relevant_schemas = get_main_response_schemas_of_operation(
            openapi_spec, operation
        )
        for schema in relevant_schemas:
            mappings_with_constraint = (
                response_body_input_parameter_mappings_with_constraint.get(schema, {})
            )

            for attr in mappings_with_constraint:
                mappings = mappings_with_constraint[attr]
                mappings = list(map(tuple, set(map(tuple, mappings))))

                attribute_description = simplified_schemas[schema].get(attr, "")
                if "(description:" not in attribute_description:
                    attribute_description = None
                else:
                    attribute_description = attribute_description.split(
                        "(description:"
                    )[-1][:-1].strip()

                for mapping in mappings:
                    corresponding_operation = mapping[0]
                    corresponding_part = mapping[1]
                    corresponding_attribute = mapping[2]

                    corresponding_attribute_description = (
                        simplified_openapi[corresponding_operation]
                        .get(corresponding_part, {})
                        .get(corresponding_attribute, "")
                    )
                    if "(description:" not in corresponding_attribute_description:
                        corresponding_attribute_description = None
                    else:
                        corresponding_attribute_description = (
                            corresponding_attribute_description.split("(description:")[
                                -1
                            ][:-1].strip()
                        )
                    new_instance = {
                        "response resource": schema,
                        "attribute": attr,
                        "description": attribute_description,
                        "attribute inferred from operation": corresponding_operation,
                        "part": corresponding_part,
                        "corresponding attribute": corresponding_attribute,
                        "corresponding attribute description": corresponding_attribute_description,
                    }
                    if new_instance not in data:
                        data.append(new_instance)

                    operations_with_constraint.add(operation)

    df = pd.DataFrame(data)
    df.to_excel(output_file, index=False)

    print(
        f"No. of operations having constraints inferred from input parameters: {len(operations_with_constraint)}"
    )


def simplify_openapi(openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplify an OpenAPI specification by extracting key information.

    This function is imported from openapi_utils.py.
    """
    from .openapi_utils import simplify_openapi

    return simplify_openapi(openapi_spec)


def get_simplified_schema(openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract simplified schema from an OpenAPI specification.

    This function is imported from openapi_utils.py.
    """
    from .openapi_utils import get_simplified_schema

    return get_simplified_schema(openapi_spec)


def get_main_response_schemas_of_operation(
    openapi_spec: Dict[str, Any], operation: str
) -> List[str]:
    """
    Get the main response schemas for a given operation.

    This function is imported from openapi_utils.py.
    """
    from .openapi_utils import get_main_response_schemas_of_operation

    return get_main_response_schemas_of_operation(openapi_spec, operation)


def get_relevent_response_schemas_of_operation(
    openapi_spec: Dict[str, Any], operation: str
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Get relevant response schemas for a given operation.

    This function is imported from openapi_utils.py.
    """
    from .openapi_utils import get_relevent_response_schemas_of_operation

    return get_relevent_response_schemas_of_operation(openapi_spec, operation)


def main():
    """
    Demonstrate the functionality of the excel_utils module.

    This function showcases:
    1. Simple JSON to Excel conversion
    2. Validated JSON to Excel conversion with Pydantic models
    3. Converting a DataFrame directly to Excel
    4. Reading an Excel file into a DataFrame
    5. Converting response property constraints
    6. Converting request-response constraints
    """
    print("Excel Utils Demonstration")
    print("=" * 50)

    # Create a sample JSON file for demonstration
    sample_data = {
        "name": ["Alice", "Bob", "Charlie", "David"],
        "age": [25, 30, 35, 40],
        "city": ["New York", "London", "Paris", "Tokyo"],
        "active": [True, False, True, True],
    }

    demo_dir = Path("d:/Projects/Desktop/RBCTest/demo")
    demo_dir.mkdir(exist_ok=True)

    # Save sample data as JSON
    json_file = demo_dir / "sample_data.json"
    with open(json_file, "w") as f:
        json.dump(sample_data, f)

    print(f"Created sample JSON file: {json_file}")

    # Example 1: Simple JSON to Excel conversion
    print("\n1. Simple JSON to Excel conversion")
    excel_file = demo_dir / "simple_output.xlsx"
    try:
        convert_json_to_excel(str(json_file), str(excel_file))
        print(f"✓ Success! Excel file created at {excel_file}")
    except Exception as e:
        print(f"✗ Error: {e}")

    # Example 2: Validated JSON to Excel conversion
    print("\n2. Validated JSON to Excel conversion")
    excel_file2 = demo_dir / "validated_output.xlsx"

    result = convert_json_to_excel_validated(
        {
            "json_file": str(json_file),
            "excel_file": str(excel_file2),
            "sheet_name": "People",
            "include_index": True,
        }
    )

    if result.success:
        print(f"✓ {result.message}")
        print(f"  - Rows processed: {result.rows_processed}")
        print(f"  - Columns processed: {result.columns_processed}")
    else:
        print(f"✗ {result.message}")

    # Example 3: DataFrame to Excel conversion
    print("\n3. DataFrame to Excel conversion")
    df = pd.DataFrame(sample_data)
    df["salary"] = [50000, 60000, 70000, 80000]  # Add an extra column

    excel_file3 = demo_dir / "dataframe_output.xlsx"
    df_result = convert_dataframe_to_excel(
        df,
        {
            "excel_file": str(excel_file3),
            "sheet_name": "EmployeeData",
            "include_index": False,
        },
    )

    if df_result.success:
        print(f"✓ {df_result.message}")
        print(f"  - Rows processed: {df_result.rows_processed}")
        print(f"  - Columns processed: {df_result.columns_processed}")
    else:
        print(f"✗ {df_result.message}")

    # Example 4: Reading Excel file into DataFrame
    print("\n4. Reading Excel file into DataFrame")
    df_read, message = excel_to_dataframe(str(excel_file3))

    if df_read is not None:
        print(f"✓ {message}")
        print("DataFrame preview:")
        print(df_read.head(2))
    else:
        print(f"✗ {message}")

    # Example 5: Converting response property constraints
    print("\n5. Converting response property constraints")
    print(
        "  Functionality available through convert_json_to_excel_response_property_constraints()"
    )

    # Example 6: Converting request-response constraints
    print("\n6. Converting request-response constraints")
    print(
        "  Functionality available through convert_json_to_excel_request_response_constraints()"
    )

    print("\nDemonstration Complete!")


if __name__ == "__main__":
    main()
