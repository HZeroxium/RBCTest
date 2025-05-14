# /src/models/evaluation_models.py

"""
Evaluation Models Module

This module defines Pydantic models for constraint evaluation and test generation evaluation.
These models provide structured representations of configuration parameters and results.
"""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ConstraintEvaluationConfig(BaseModel):
    """Configuration parameters for constraint evaluation."""

    approach_folder: str = Field(
        ..., description="Folder containing the approach results to evaluate"
    )
    ground_truth_folder: str = Field(
        ..., description="Folder containing the ground truth data"
    )
    api_folders: List[str] = Field(..., description="List of API folders to evaluate")
    output_csv_path: str = Field(
        ..., description="Path where the evaluation results CSV will be saved"
    )
    export: bool = Field(
        True, description="Whether to export the results to a CSV file"
    )
    verifier: bool = Field(
        False, description="Whether to verify constraints during evaluation"
    )


class TestGenEvaluationConfig(BaseModel):
    """Configuration parameters for test generation evaluation."""

    approach_folder: str = Field(
        ..., description="Folder containing the approach results to evaluate"
    )
    api_folders: List[str] = Field(..., description="List of API folders to evaluate")
    output_csv_path: str = Field(
        ..., description="Path where the evaluation results CSV will be saved"
    )
    ground_truth_folder: Optional[str] = Field(
        None, description="Folder containing the ground truth data (if needed)"
    )


class CategoryStats(BaseModel):
    """Statistics for a category of constraints."""

    all_count: int = Field(0, description="Total number of constraints")
    no_test_gen_count: int = Field(0, description="Number of constraints without tests")
    correct_count: int = Field(0, description="Number of correct test generations")
    tp_satisfied_count: int = Field(
        0, description="Number of true positive satisfied constraints"
    )
    tp_mismatched_count: int = Field(
        0, description="Number of true positive mismatched constraints"
    )
    unknown_count: int = Field(0, description="Number of unknown status constraints")


class TestGenSummary(BaseModel):
    """Summary of test generation evaluation results."""

    api_stats: Dict[str, CategoryStats] = Field(
        default_factory=dict, description="Statistics for each API, keyed by API name"
    )
    total_stats: CategoryStats = Field(
        default_factory=CategoryStats, description="Total statistics across all APIs"
    )
