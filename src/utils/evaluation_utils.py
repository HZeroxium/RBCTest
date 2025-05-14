# /src/utils/evaluation_utils.py

"""
Evaluation Utilities Module

This module provides utility functions for evaluating constraint mining and test generation.
"""

import os
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional


def categorize_constraint(excel_file: str, knowledge_base_file: str) -> None:
    """
    Categorize constraints based on a knowledge base.

    Args:
        excel_file: Path to the Excel file containing constraints
        knowledge_base_file: Path to the knowledge base Excel file

    Returns:
        None (updates the Excel file in place)
    """
    print(f"Categorizing {excel_file}")

    try:
        df = pd.read_excel(excel_file, engine="openpyxl")
        kb_df = pd.read_excel(knowledge_base_file, engine="openpyxl")

        if df.empty or kb_df.empty:
            print(f"Either {excel_file} or {knowledge_base_file} is empty")
            return

        for row, data in df.iterrows():
            description = data["description"]
            if "corresponding attribute description" in df.columns:
                description = data["corresponding attribute description"]

            # Find the description in the knowledge base
            mask = kb_df["description"] == description
            found_mapping = kb_df[mask]

            if found_mapping.empty:
                print(f"Cannot find '{description}' in knowledge base")
                continue

            category = found_mapping["category of constraint"].values[0]
            df.at[row, "category of constraint"] = category

        # Save the updated dataframe
        df.to_excel(excel_file, index=False)

    except Exception as e:
        print(f"Error categorizing constraints: {e}")


def summarize_test_gen_response(
    excel_file: str, summary_dict: Dict[str, Dict[str, int]], api_name: str
) -> Tuple[Dict[str, Dict[str, int]], pd.DataFrame]:
    """
    Summarize test generation results from an Excel file.

    Args:
        excel_file: Path to the Excel file containing test generation results
        summary_dict: Dictionary to update with summary information
        api_name: Name of the API

    Returns:
        A tuple containing (updated_summary_dict, true_mismatched_dataframe)
    """
    print(f"Excel file: {excel_file}")

    try:
        # Read Excel file with string dtype for all columns
        df = pd.read_excel(excel_file, engine="openpyxl", dtype=str)
        true_mismatched_df = pd.DataFrame()

        if df.empty:
            return summary_dict, true_mismatched_df

        # Check required columns
        required_columns = ["constraint_correctness", "correctness_of_script"]
        if not all(col in df.columns for col in required_columns):
            print(
                f"Excel file {excel_file} is missing required columns: {required_columns}"
            )
            return summary_dict, true_mismatched_df

        # Filter true positive constraints
        tp_df = df[df["constraint_correctness"] == "TP"]

        # Determine correct test criteria based on first row
        if len(tp_df) > 0:
            first_row = tp_df.iloc[0]["correctness_of_script"]
            if first_row == "correct" or first_row == "incorrect":
                correct_df = tp_df[tp_df["correctness_of_script"] == "correct"]
            else:
                correct_df = tp_df[tp_df["correctness_of_script"] == "True"]

            # Get counts for different status types
            truely_satisfied_df = correct_df[(correct_df["status"] == "satisfied")]
            truely_mismatched_df = correct_df[(correct_df["status"] == "mismatched")]
            truely_unknown_df = correct_df[correct_df["status"] == "unknown"]

            # Update summary dictionary
            summary_dict[api_name] = {
                "All": len(df),
                "No test gen": len(tp_df),
                "correct": len(correct_df),
                "TP_satisfied": len(truely_satisfied_df),
                "TP_mismatched": len(truely_mismatched_df),
                "unknown": len(truely_unknown_df),
            }

            # Add API field to mismatched dataframe
            if not truely_mismatched_df.empty:
                truely_mismatched_df["API"] = api_name

        return summary_dict, truely_mismatched_df

    except Exception as e:
        print(f"Error summarizing test generation: {e}")
        return summary_dict, pd.DataFrame()
