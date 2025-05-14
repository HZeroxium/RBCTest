# /src/models/example_models.py

"""
Example Models Module

This module defines Pydantic models for working with example values in OpenAPI specifications.
"""

from typing import Dict, List, Optional, Any, Union, Literal
from pathlib import Path
from pydantic import BaseModel, Field, field_validator


class OpenAPIProperty(BaseModel):
    """Model for an OpenAPI property definition."""

    type: Optional[str] = Field(None, description="The data type of the property")
    format: Optional[str] = Field(None, description="The format of the property")
    description: Optional[str] = Field(None, description="Description of the property")
    example: Optional[Any] = Field(None, description="Example value for the property")
    enum: Optional[List[Any]] = Field(None, description="Possible enum values")
    default: Optional[Any] = Field(None, description="Default value")


class ExampleSearchOptions(BaseModel):
    """Configuration options for searching for example values."""

    check_components: bool = Field(
        True, description="Whether to check in OpenAPI 3.0 components section"
    )
    check_definitions: bool = Field(
        True, description="Whether to check in OpenAPI 2.0 definitions section"
    )
    use_brute_force: bool = Field(
        True, description="Whether to use brute force search as a fallback"
    )
    use_enum_values: bool = Field(
        True, description="Whether to use enum values if no example is found"
    )
    use_default_values: bool = Field(
        True, description="Whether to use default values if no example is found"
    )


class ExampleSearchResult(BaseModel):
    """Result of searching for an example value."""

    object_name: str = Field(..., description="Name of the object containing the field")
    field_name: str = Field(..., description="Name of the field")
    example_value: Optional[Any] = Field(None, description="Found example value")
    source: Literal[
        "components", "definitions", "brute_force", "enum", "default", "none"
    ] = Field("none", description="Source of the example value")
    found: bool = Field(
        False, description="Whether an example value was successfully found"
    )


class VerifierConfig(BaseModel):
    """Configuration for the Example Verifier."""

    root_folder: Path = Field(..., description="Root folder containing API data")
    api_spec_folder: Path = Field(
        ..., description="Folder containing API specifications"
    )
    output_suffix: str = Field(
        "_example_value", description="Suffix to add to output files"
    )
    search_options: ExampleSearchOptions = Field(
        default_factory=ExampleSearchOptions, description="Options for example search"
    )

    @field_validator("root_folder", "api_spec_folder")
    def validate_path_exists(cls, v: Path) -> Path:
        """Validate that the path exists."""
        if not v.exists():
            raise ValueError(f"Path does not exist: {v}")
        return v

    @classmethod
    def from_strings(cls, root_folder: str, api_spec_folder: str) -> "VerifierConfig":
        """Create a VerifierConfig from string paths."""
        return cls(
            root_folder=Path(root_folder),
            api_spec_folder=Path(api_spec_folder),
            search_options=ExampleSearchOptions(),
        )


class VerifierResult(BaseModel):
    """Results from running the verifier."""

    total_constraints: int = Field(0, description="Total number of constraints checked")
    examples_found: int = Field(0, description="Number of examples found")
    apis_processed: List[str] = Field(
        default_factory=list, description="List of APIs that were processed"
    )
    failure_rate: float = Field(
        0.0, description="Percentage of constraints without examples"
    )

    def calculate_stats(self) -> None:
        """Calculate statistics based on the current counts."""
        self.failure_rate = (
            (self.total_constraints - self.examples_found)
            / self.total_constraints
            * 100
            if self.total_constraints > 0
            else 0.0
        )

    def __str__(self) -> str:
        """Return a string representation of the results."""
        return (
            f"Found example values for {self.examples_found}/{self.total_constraints} "
            f"constraints ({100 - self.failure_rate:.1f}% success rate)"
        )
