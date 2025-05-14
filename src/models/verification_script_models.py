# /src/models/verification_script_models.py

"""
Verification Script Models

This module defines Pydantic models for verification script generation and execution.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator
import os


class VerificationScriptConfig(BaseModel):
    """Configuration for verification script generation."""

    service_name: str = Field(
        ..., description="Name of the service to generate verification scripts for"
    )
    experiment_dir: str = Field(
        ..., description="Directory to store experiment outputs"
    )
    request_response_constraints_file: Optional[str] = Field(
        None, description="Path to Excel file containing request-response constraints"
    )
    response_property_constraints_file: Optional[str] = Field(
        None, description="Path to Excel file containing response property constraints"
    )

    @field_validator("experiment_dir")
    def ensure_experiment_dir_exists(cls, v: str) -> str:
        """Ensure the experiment directory exists."""
        if not os.path.exists(v):
            os.makedirs(v, exist_ok=True)
        return v


class ConstraintInfo(BaseModel):
    """Information about a constraint to verify."""

    operation: str = Field(..., description="API operation ID")
    response_resource: str = Field(..., description="Response resource name")
    attribute: str = Field(..., description="Attribute name")
    description: str = Field(..., description="Constraint description")


class RequestResponseConstraintInfo(ConstraintInfo):
    """Information about a request-response constraint to verify."""

    corresponding_operation: str = Field(
        ..., description="Operation that generates this constraint"
    )
    corresponding_part: str = Field(
        ..., description="Part of the operation (parameters or requestBody)"
    )
    corresponding_attribute: str = Field(
        ..., description="Attribute name in the request"
    )
    corresponding_description: str = Field(
        ..., description="Description of the attribute in the request"
    )


class VerificationScriptResult(BaseModel):
    """Result of a verification script generation."""

    verification_script: str = Field(
        "", description="Generated verification script code"
    )
    executable_script: str = Field(
        "", description="Executable version of the verification script"
    )
    status: Literal["satisfied", "mismatched", "unknown", "code error"] = Field(
        "unknown", description="Status of script execution"
    )
    confirmation: str = Field("", description="Confirmation of script correctness")
    revised_script: str = Field(
        "", description="Revised script if the original was not confirmed"
    )
    revised_executable_script: str = Field(
        "", description="Executable version of the revised script"
    )
    revised_status: str = Field(
        "", description="Status of the revised script execution"
    )


class ResponsePropertyVerificationResult(VerificationScriptResult):
    """Result of response property verification."""

    operation: str = Field(..., description="API operation ID")
    response_resource: str = Field(..., description="Response resource name")
    attribute: str = Field(..., description="Attribute name")
    description: str = Field(..., description="Constraint description")


class RequestResponseVerificationResult(VerificationScriptResult):
    """Result of request-response verification."""

    operation: str = Field(..., description="API operation ID")
    response_resource: str = Field(..., description="Response resource name")
    attribute: str = Field(..., description="Response attribute name")
    description: str = Field(
        ..., description="Response attribute constraint description"
    )
    corresponding_operation: str = Field(..., description="Corresponding operation")
    corresponding_attribute: str = Field(
        ..., description="Corresponding request attribute"
    )
    corresponding_description: str = Field(
        ..., description="Corresponding request attribute description"
    )
