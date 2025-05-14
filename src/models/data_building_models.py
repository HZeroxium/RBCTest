# /src/models/data_building_models.py

"""
Data Models for Response Body Verification

This module defines Pydantic models used for data model building
and schema relationship analysis.
"""

from typing import Dict, List, Tuple, Optional, Set, Any, Union
from pydantic import BaseModel, Field, field_validator
import os
import json


class SchemaKeyPair(BaseModel):
    """A pair of keys that represent the same concept across two schemas."""

    source_field: str = Field(..., description="Field name in the source schema")
    target_field: str = Field(..., description="Field name in the target schema")

    def to_tuple(self) -> Tuple[str, str]:
        """Convert to a simple tuple representation."""
        return (self.source_field, self.target_field)

    @classmethod
    def from_tuple(cls, pair_tuple: Tuple[str, str]) -> "SchemaKeyPair":
        """Create from a tuple representation."""
        return cls(source_field=pair_tuple[0], target_field=pair_tuple[1])


class SchemaRelationship(BaseModel):
    """Represents the relationship between two schemas."""

    schema_pair: Tuple[str, str] = Field(
        ..., description="Pair of schema names that are related"
    )
    field_mappings: List[SchemaKeyPair] = Field(
        default_factory=list,
        description="List of field mappings between the two schemas",
    )


class DataModel(BaseModel):
    """Complete data model containing schema keys and relationships."""

    schema_keys: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Dictionary mapping schema names to their key fields",
    )
    schema_relationships: List[SchemaRelationship] = Field(
        default_factory=list, description="List of relationships between schemas"
    )

    @classmethod
    def from_legacy_format(cls, legacy_data: Dict[str, Any]) -> "DataModel":
        """
        Convert from the legacy format used in the original implementation.

        Args:
            legacy_data: Dictionary in the legacy format with 'schema_keys' and 'schema_model'

        Returns:
            DataModel instance populated with the legacy data
        """
        schema_keys = legacy_data.get("schema_keys", {})

        # Extract schema relationships
        schema_relationships = []
        if "schema_model" in legacy_data and len(legacy_data["schema_model"]) >= 2:
            schema_pairs = legacy_data["schema_model"][0]
            field_mappings_list = legacy_data["schema_model"][1]

            for i, schema_pair in enumerate(schema_pairs):
                if i < len(field_mappings_list):
                    field_mappings = [
                        SchemaKeyPair(source_field=src, target_field=tgt)
                        for src, tgt in field_mappings_list[i]
                    ]
                    schema_relationships.append(
                        SchemaRelationship(
                            schema_pair=schema_pair, field_mappings=field_mappings
                        )
                    )

        return cls(schema_keys=schema_keys, schema_relationships=schema_relationships)

    def to_legacy_format(self) -> Dict[str, Any]:
        """
        Convert to the legacy format for backward compatibility.

        Returns:
            Dictionary in the legacy format with 'schema_keys' and 'schema_model'
        """
        schema_pairs = []
        field_mappings_list = []

        for relationship in self.schema_relationships:
            schema_pairs.append(relationship.schema_pair)
            field_mappings_list.append(
                [mapping.to_tuple() for mapping in relationship.field_mappings]
            )

        return {
            "schema_keys": self.schema_keys,
            "schema_model": [schema_pairs, field_mappings_list],
        }


class DataModelBuilderConfig(BaseModel):
    """Configuration for the DataModelBuilder."""

    openapi_path: str = Field(..., description="Path to the OpenAPI specification file")
    ks_project_path: Optional[str] = Field(
        None, description="Path to the KAT Plugin project directory"
    )
    data_types_to_keep: Set[str] = Field(
        default_factory=lambda: {"integer", "string"},
        description="Set of data types to keep during attribute filtering",
    )

    @field_validator("openapi_path")
    def validate_openapi_path(cls, v: str) -> str:
        """Validate that the OpenAPI path exists."""
        if not os.path.exists(v):
            raise ValueError(f"OpenAPI specification file not found at: {v}")
        return v

    @field_validator("ks_project_path")
    def validate_ks_project_path(cls, v: Optional[str]) -> Optional[str]:
        """Validate that the KS project path exists if provided."""
        if v is not None and not os.path.exists(v):
            raise ValueError(f"KS project directory not found at: {v}")
        return v
