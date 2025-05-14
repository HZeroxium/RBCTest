# /src/models/execution_models.py

"""
Execution Models Module

This module defines Pydantic models for code execution processes.
These models provide structured representations of configuration parameters and results.
"""

from typing import Dict, List, Optional, Union, Literal
from pydantic import BaseModel, Field


class ExecutionConfig(BaseModel):
    """Configuration for code execution."""

    excel_path: str = Field(
        ..., description="Path to the Excel file containing verification scripts"
    )
    is_request_response: bool = Field(
        False, description="Whether this is a request-response constraint"
    )
    dataset_folder: Optional[str] = Field(
        None, description="Folder containing the dataset files"
    )


class ExecutionStats(BaseModel):
    """Statistics from code execution."""

    satisfied_count: int = Field(0, description="Number of satisfied executions")
    mismatched_count: int = Field(0, description="Number of mismatched executions")
    unknown_count: int = Field(0, description="Number of unknown status executions")
    code_error_count: int = Field(
        0, description="Number of executions with code errors"
    )
    total_count: int = Field(0, description="Total number of executions")


class ExecutionResult(BaseModel):
    """Result of code execution."""

    status: Literal["satisfied", "mismatched", "unknown", "code error"] = Field(
        ..., description="Status of the execution"
    )
    script: str = Field(..., description="The executed script")
    index: int = Field(..., description="Index in the Excel file")
