# /src/models/evaluation_models.py

"""
Evaluation Models

This module defines Pydantic models for evaluation operations including
constraint mining evaluation, test generation evaluation, and invariant evaluation.
"""

from typing import Dict, List, Union
from pydantic import BaseModel, Field, field_validator
from pathlib import Path


class EvaluationConfig(BaseModel):
    """Configuration for constraint mining evaluation."""

    approach_folder: Path = Field(
        ..., description="Folder containing the approach results to evaluate"
    )
    ground_truth_folder: Path = Field(
        ..., description="Folder containing the ground truth data"
    )
    api_folders: List[str] = Field(..., description="List of API folders to evaluate")
    output_csv: Path = Field(
        ..., description="Path where the evaluation results CSV will be saved"
    )
    export_results: bool = Field(
        False, description="Whether to export the results to the original files"
    )
    apply_verification_filter: bool = Field(
        False, description="Whether to filter results based on verification results"
    )

    @field_validator("approach_folder", "ground_truth_folder")
    def folder_must_exist(cls, v):
        """Validate that the folder exists."""
        if not v.exists():
            raise ValueError(f"Folder does not exist: {v}")
        return v

    @classmethod
    def from_paths(
        cls,
        approach_folder: str,
        ground_truth_folder: str,
        output_csv: str,
        api_folders: List[str],
        export_results: bool = False,
        apply_verification_filter: bool = False,
    ) -> "EvaluationConfig":
        """Create a configuration from string paths."""
        return cls(
            approach_folder=Path(approach_folder),
            ground_truth_folder=Path(ground_truth_folder),
            output_csv=Path(output_csv),
            api_folders=api_folders,
            export_results=export_results,
            apply_verification_filter=apply_verification_filter,
        )


class EvaluationResults(BaseModel):
    """Results of constraint mining evaluation."""

    api_name: str = Field(..., description="Name of the API being evaluated")
    constraint_type: str = Field(
        ..., description="Type of constraint (Response-property or Request-Response)"
    )
    true_positives: int = Field(..., description="Number of true positives")
    false_positives: int = Field(..., description="Number of false positives")
    false_negatives: int = Field(..., description="Number of false negatives")
    precision: Union[float, str] = Field(
        ..., description="Precision as a percentage or '-' if not applicable"
    )
    recall: Union[float, str] = Field(
        ..., description="Recall as a percentage or '-' if not applicable"
    )
    f1_score: Union[float, str] = Field(
        ..., description="F1 score as a percentage or '-' if not applicable"
    )


class TestGenResults(BaseModel):
    """Results of test generation evaluation."""

    api_name: str = Field(..., description="Name of the API being evaluated")
    constraint_type: str = Field(
        ..., description="Type of constraint (Response-property or Request-Response)"
    )
    total_constraints: int = Field(..., description="Total number of constraints")
    correct_constraints: int = Field(..., description="Number of correct constraints")
    accuracy: float = Field(..., description="Accuracy as a percentage")
    false_negatives: int = Field(..., description="Number of false negatives")
    recall: Union[float, str] = Field(
        ..., description="Recall as a percentage or '-' if not applicable"
    )
    f1_score: Union[float, str] = Field(
        ..., description="F1 score as a percentage or '-' if not applicable"
    )

    # With verification filter applied
    filtered_total: int = Field(
        ..., description="Total number of constraints after verification filter"
    )
    filtered_correct: int = Field(
        ..., description="Number of correct constraints after verification filter"
    )
    filtered_accuracy: float = Field(
        ..., description="Accuracy after verification filter as a percentage"
    )
    filtered_false_negatives: int = Field(
        ..., description="Number of false negatives after verification filter"
    )
    filtered_recall: Union[float, str] = Field(
        ...,
        description="Recall after verification filter as a percentage or '-' if not applicable",
    )
    filtered_f1_score: Union[float, str] = Field(
        ...,
        description="F1 score after verification filter as a percentage or '-' if not applicable",
    )


class CategoryStatistics(BaseModel):
    """Statistics about constraint categories."""

    type: str = Field(..., description="Constraint type")
    category_counts: Dict[str, int] = Field(
        default_factory=dict, description="Count of constraints by category"
    )


class InvariantRecord(BaseModel):
    """Represents an invariant record from the CSV file."""

    pptname: str = Field(..., description="Property name")
    invariant: str = Field(..., description="Invariant definition")
    invariantType: str = Field(..., description="Type of invariant")
    variables: str = Field(..., description="Variables in the invariant")
    postmanAssertion: str = Field(..., description="Associated Postman assertion")
    description: str = Field(..., description="Description of the invariant")
    eval: str = Field("", description="Evaluation result ('t' for true, 'f' for false)")


class InvariantEvaluatorConfig(BaseModel):
    """Configuration for the invariant evaluator application."""

    csv_file: Path = Field(
        ..., description="Path to the CSV file containing invariants"
    )
    encoding: str = Field("utf-8", description="Encoding of the CSV file")
    separator: str = Field("\t", description="Separator used in the CSV file")
    output_encoding: str = Field(
        "utf-16", description="Encoding for the output CSV file"
    )
    font_family: str = Field("Arial", description="Font family for the UI")

    @field_validator("csv_file")
    def file_must_exist(cls, v):
        """Validate that the file exists."""
        if not v.exists():
            raise ValueError(f"CSV file does not exist: {v}")
        return v

    @classmethod
    def from_path(cls, csv_file: str) -> "InvariantEvaluatorConfig":
        """Create a configuration from a string path."""
        return cls(csv_file=Path(csv_file))
