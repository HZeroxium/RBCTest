# /src/models/mapping_models.py

"""
Mapping Models Module

This module defines Pydantic models representing the data structures used in the
parameter-response body mapping process, with detailed field descriptions and validation.
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from pydantic import BaseModel, Field


class AttributeInfo(BaseModel):
    """Information about an attribute in a schema."""

    name: str = Field(..., description="The name of the attribute")
    value: str = Field(..., description="The value or description of the attribute")

    def to_tuple(self) -> Tuple[str, str]:
        """Convert to a tuple for easier comparison."""
        return (self.name, self.value)


class FoundMapping(BaseModel):
    """A mapping that has been found and validated during processing."""

    parameter_name: str = Field(..., description="The name of the input parameter")
    parameter_description: str = Field(
        ..., description="The description of the input parameter"
    )
    schema_name: str = Field(
        ..., description="The name of the schema containing the target attribute"
    )
    corresponding_attribute: Optional[str] = Field(
        None,
        description="The name of the corresponding attribute in the schema, if found",
    )

    def to_list(self) -> List[Any]:
        """Convert to the legacy list format for backward compatibility."""
        return [
            self.parameter_name,
            self.parameter_description,
            self.schema_name,
            self.corresponding_attribute,
        ]

    @classmethod
    def from_list(cls, mapping_list: List[Any]) -> "FoundMapping":
        """Create a FoundMapping from a list in the legacy format."""
        if len(mapping_list) >= 4:
            return cls(
                parameter_name=mapping_list[0],
                parameter_description=mapping_list[1],
                schema_name=mapping_list[2],
                corresponding_attribute=mapping_list[3],
            )
        raise ValueError("Invalid mapping list format")


class SchemaMapping(BaseModel):
    """Mapping of attributes in a schema to operations that use them."""

    attributes: Dict[str, List[List[str]]] = Field(
        default_factory=dict,
        description="Dictionary mapping attributes to lists of operations using them",
    )


class ParameterResponseMapperConfig(BaseModel):
    """Configuration for the Parameter-Response Mapper."""

    openapi_path: str = Field(..., description="Path to the OpenAPI specification file")
    except_attributes_found_constraints_inside_response_body: bool = Field(
        False,
        description="Whether to exclude attributes that have constraints inside response body",
    )
    save_and_load: bool = Field(
        False, description="Whether to save and load progress from files"
    )
    list_of_available_schemas: Optional[List[str]] = Field(
        None,
        description="Optional list of schemas to process; if None, all schemas are processed",
    )
    outfile: Optional[str] = Field(
        None, description="Path to the output file for saving results"
    )
    experiment_folder: str = Field(
        "experiment_our", description="Folder where experiment files are stored"
    )
    is_naive: bool = Field(
        False, description="Whether to use the naive mapping approach"
    )
