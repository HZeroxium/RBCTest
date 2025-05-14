# /src/models/constraint_models.py

"""
Constraint Models Module

This module defines Pydantic models for representing constraints in REST APIs,
including parameter and response constraints extracted from OpenAPI specifications.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class CheckedMapping(BaseModel):
    """A model representing a mapping that has been checked for constraints."""

    mapping: List[str] = Field(
        ..., description="List containing [operation, part, parameter] information"
    )
    confirmation: str = Field(
        ..., description="Confirmation status of the mapping ('yes' or 'no')"
    )

    def to_list(self) -> List[Any]:
        """
        Convert the model to a list representation for backward compatibility.

        Returns:
            A list containing [mapping, confirmation]
        """
        return [self.mapping, self.confirmation]


class AttributeMapping(BaseModel):
    """A model representing mapping between an attribute and operations."""

    attribute_name: str = Field(
        ..., description="The name of the attribute in the schema"
    )
    attribute_value: str = Field(
        ..., description="The value/description of the attribute"
    )


class ConstraintExtractorConfig(BaseModel):
    """Configuration for constraint extraction process."""

    openapi_path: str = Field(..., description="Path to the OpenAPI specification file")
    save_and_load: bool = Field(
        False, description="Whether to save and load progress from files"
    )
    list_of_operations: Optional[List[str]] = Field(
        None,
        description="Optional list of operations to process; if None, all operations are processed",
    )
    experiment_folder: str = Field(
        "experiment", description="Folder where experiment files are stored"
    )


class ResponseBodyConstraint(BaseModel):
    """A model representing a constraint in a response body."""

    schema: str = Field(..., description="The schema name containing the constraint")
    attribute: str = Field(..., description="The attribute name with the constraint")
    description: str = Field(
        ..., description="The description that defines the constraint"
    )


class InputParameterConstraint(BaseModel):
    """A model representing a constraint in an input parameter."""

    operation: str = Field(..., description="The operation containing the parameter")
    part: str = Field(
        ..., description="The part of the operation ('parameters' or 'requestBody')"
    )
    parameter: str = Field(..., description="The parameter name with the constraint")
    description: str = Field(
        ..., description="The description that defines the constraint"
    )


class ResponseBodyConstraints(BaseModel):
    """A collection of response body constraints organized by schema."""

    constraints: Dict[str, Dict[str, str]] = Field(
        default_factory=dict,
        description="Mapping of schema names to attribute constraints",
    )

    def to_dict(self) -> Dict[str, Dict[str, str]]:
        """
        Convert the model to a dictionary representation.

        Returns:
            Dictionary representation of the constraints
        """
        return self.constraints

    @classmethod
    def from_dict(cls, data: Dict[str, Dict[str, str]]) -> "ResponseBodyConstraints":
        """
        Create a model from a dictionary.

        Args:
            data: Dictionary containing constraint data

        Returns:
            ResponseBodyConstraints model
        """
        return cls(constraints=data)


class InputParameterConstraints(BaseModel):
    """A collection of input parameter constraints organized by operation."""

    constraints: Dict[str, Dict[str, Dict[str, str]]] = Field(
        default_factory=dict,
        description="Mapping of operations to parameter constraints",
    )

    def to_dict(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        """
        Convert the model to a dictionary representation.

        Returns:
            Dictionary representation of the constraints
        """
        return self.constraints

    @classmethod
    def from_dict(
        cls, data: Dict[str, Dict[str, Dict[str, str]]]
    ) -> "InputParameterConstraints":
        """
        Create a model from a dictionary.

        Args:
            data: Dictionary containing constraint data

        Returns:
            InputParameterConstraints model
        """
        return cls(constraints=data)
