# /src/models/verification_models.py

"""
Verification Models Module

This module defines Pydantic models for constraint verification process.
These models provide structured representations of configuration parameters and results.
"""

from typing import Dict, List, Optional, Union, Any, Literal
from pydantic import BaseModel, Field


class VerificationConfig(BaseModel):
    """Configuration for constraint verification process."""

    root_folder: str = Field(..., description="Root folder containing constraint data")
    api_spec_folder: str = Field(
        ..., description="Folder containing API specifications"
    )
    executable: str = Field(
        "python", description="Executable to use for running verification scripts"
    )


class FieldVerificationResult(BaseModel):
    """Result of a single field verification."""

    status: Literal["satisfied", "mismatched", "unknown", "code error"] = Field(
        ..., description="Status of the verification"
    )
    executable_script: str = Field(
        ..., description="The executable script that was generated"
    )


class ConstraintVerificationResult(BaseModel):
    """Result of constraint verification."""

    field_name: str = Field(..., description="Name of the field being verified")
    example_value: Any = Field(..., description="Example value used for verification")
    verification_results: List[FieldVerificationResult] = Field(
        default_factory=list, description="Results of individual field verifications"
    )
    satisfied_count: int = Field(0, description="Count of satisfied verifications")
    mismatched_count: int = Field(0, description="Count of mismatched verifications")
    unknown_count: int = Field(0, description="Count of unknown verifications")
    code_error_count: int = Field(
        0, description="Count of code errors during verification"
    )
    overall_status: Literal["satisfied", "mismatched", "unknown", "code error"] = Field(
        "unknown", description="Overall verification status"
    )
