# /src/eval/response_approach_evaluate.py

"""
Response Property Constraint Evaluation

This module provides functions for evaluating response property constraint mining
and test generation results against ground truth data.
"""

import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union, Optional, cast

from models.evaluation_models import (
    EvaluationConfig,
    EvaluationResults,
    TestGenResults,
    CategoryStatistics,
)


# Define constant for the constraint type
CONSTRAINT_TYPE = "Response-property"


def evaluate_response_property_constraint_mining(
    config: EvaluationConfig,
) -> List[EvaluationResults]:
    """
    Evaluate response property constraint mining against ground truth.

    Args:
        config: Configuration for the evaluation

    Returns:
        A list of evaluation results for each API

    This function compares the mined constraints in the approach folder against
    the ground truth constraints and calculates precision, recall, and F1 scores.
    """
    # Create the output CSV file if it doesn't exist
    if not config.output_csv.exists():
        with open(config.output_csv, "w") as f:
            f.write("API,Constraint_Type,TP,FP,FN,Precision,Recall,F1\n")

    # Dictionary to store category statistics
    categories_dict: Dict[str, Dict[str, Union[str, int]]] = {}

    # DataFrame to collect false negatives
    all_fns = pd.DataFrame()

    # List to store evaluation results
    results: List[EvaluationResults] = []

    # Process each API folder
    for api_folder in config.api_folders:
        # Skip macOS system files
        if api_folder == ".DS_Store":
            continue

        # Define file paths
        approach_file = (
            config.approach_folder / api_folder / "response_property_constraints.xlsx"
        )
        ground_truth_file = (
            config.ground_truth_folder
            / api_folder
            / "response_property_constraints.xlsx"
        )

        # Skip if either file doesn't exist
        if not approach_file.exists() or not ground_truth_file.exists():
            continue

        # Load the ground truth data
        ground_truth_df = pd.read_excel(ground_truth_file, engine="openpyxl")

        print(f"Processing {approach_file}, on {ground_truth_file}")

        # Load the approach data
        approach_df = pd.read_excel(approach_file, engine="openpyxl")
        if approach_df.empty:
            continue

        # Initialize category statistics for this API
        if api_folder not in categories_dict:
            categories_dict[api_folder] = {"type": CONSTRAINT_TYPE}

        # Apply verification filter if specified
        if config.apply_verification_filter:
            approach_df = approach_df[approach_df["verify_result"] != 0]

        # Evaluate each constraint in the approach dataframe
        approach_df["constraint_correctness"] = ""
        approach_df["category"] = ""

        for row, data in approach_df.iterrows():
            description = data["description"]

            # Find matching constraints in the ground truth
            mask = ground_truth_df["description"] == description
            found_mapping = ground_truth_df[mask]

            if found_mapping.empty:
                # False positive
                approach_df.at[row, "constraint_correctness"] = "FP"
            else:
                # True positive
                approach_df.at[row, "constraint_correctness"] = "TP"

                # If 'tp' column exists, track categories for correct constraints
                if "tp" in approach_df.columns:
                    if approach_df.at[row, "tp"] == 1:
                        # Add category information for true positives
                        category = found_mapping["category"].values[0]
                        approach_df.at[row, "category"] = category

                        # Count constraints by category
                        if category not in categories_dict[api_folder]:
                            categories_dict[api_folder][category] = 0
                        categories_dict[api_folder][category] = (
                            cast(int, categories_dict[api_folder][category]) + 1
                        )
                    else:
                        # Track categories for constraints with incorrect scripts
                        category = f"{found_mapping['category'].values[0]}_FP"
                        if category not in categories_dict[api_folder]:
                            categories_dict[api_folder][category] = 0
                        categories_dict[api_folder][category] = (
                            cast(int, categories_dict[api_folder][category]) + 1
                        )

        # Export updated dataframe if requested
        if config.export_results:
            approach_df.to_excel(approach_file, index=False)

        # Extract unique constraints for comparison
        approach_df_unique = approach_df[
            ["attribute", "description", "operation"]
        ].drop_duplicates()
        ground_truth_df_unique = ground_truth_df[
            ["attribute", "description", "operation"]
        ].drop_duplicates()

        # Create concatenated fields for comparison
        ground_truth_df_unique["concat"] = (
            ground_truth_df_unique["attribute"]
            + ground_truth_df_unique["description"]
            + ground_truth_df_unique["operation"]
        )

        approach_df_unique["concat"] = (
            approach_df_unique["attribute"]
            + approach_df_unique["description"]
            + approach_df_unique["operation"]
        )

        # Find true positives, false positives, and false negatives
        gt_values = set(ground_truth_df_unique["concat"].values)
        approach_values = set(approach_df_unique["concat"].values)

        tps = gt_values.intersection(approach_values)
        fps = approach_values - gt_values
        fns = gt_values - approach_values

        # Calculate precision, recall, and F1 score
        if len(tps) + len(fps) > 0:
            precision = len(tps) / (len(tps) + len(fps))
        else:
            precision = 0.0

        if len(tps) + len(fns) > 0:
            recall = len(tps) / (len(tps) + len(fns))
        else:
            recall = 0.0

        if precision + recall > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
        else:
            f1 = 0.0

        # Format scores as percentages rounded to one decimal place
        precision_pct = round(precision * 100, 1)
        recall_pct = round(recall * 100, 1)
        f1_pct = round(f1 * 100, 1)

        # Collect false negatives
        fns_df = ground_truth_df_unique[
            ~ground_truth_df_unique["concat"].isin(approach_df_unique["concat"])
        ]
        all_fns = pd.concat([all_fns, fns_df])

        # Append results to output CSV
        with open(config.output_csv, "a") as f:
            f.write(
                f"{api_folder},{CONSTRAINT_TYPE},{len(tps)},{len(fps)},{len(fns)},"
                f"{precision_pct},{recall_pct},{f1_pct}\n"
            )

        # Create and store evaluation result
        result = EvaluationResults(
            api_name=api_folder,
            constraint_type=CONSTRAINT_TYPE,
            true_positives=len(tps),
            false_positives=len(fps),
            false_negatives=len(fns),
            precision=precision_pct,
            recall=recall_pct,
            f1_score=f1_pct,
        )
        results.append(result)

    # Save category statistics
    save_category_statistics(config.approach_folder, categories_dict)

    # Save false negatives
    if not all_fns.empty:
        fn_output_path = config.approach_folder / f"{CONSTRAINT_TYPE}_fns.xlsx"
        all_fns.to_excel(fn_output_path, index=False)

    return results


def evaluate_response_property_test_gen(
    config: EvaluationConfig,
) -> List[TestGenResults]:
    """
    Evaluate response property test generation against ground truth.

    Args:
        config: Configuration for the evaluation

    Returns:
        A list of test generation evaluation results for each API

    This function evaluates the generated tests for response property constraints
    and calculates accuracy, recall, and F1 scores.
    """
    # Create the output CSV file if it doesn't exist
    csv_file_path = config.output_csv
    if not csv_file_path.exists():
        with open(csv_file_path, "w") as f:
            f.write(
                "API,Constraint_Type,total,total_correct,accuracy,fn,recall,f1,"
                "filter,filter_correct,filter_accuracy,filter_fn,filter_recall,filter_f1\n"
            )

    # List to store test generation results
    results: List[TestGenResults] = []

    # Process each API folder
    for api_folder in config.api_folders:
        # Skip macOS system files
        if api_folder == ".DS_Store":
            continue

        # Define file paths
        approach_file = (
            config.approach_folder / api_folder / "response_property_constraints.xlsx"
        )
        ground_truth_file = (
            config.ground_truth_folder
            / api_folder
            / "response_property_constraints.xlsx"
        )

        # Skip if either file doesn't exist
        if not approach_file.exists() or not ground_truth_file.exists():
            continue

        print(f"Evaluating test generation for {approach_file}")

        # Load approach and ground truth data
        approach_df = pd.read_excel(approach_file, engine="openpyxl")
        ground_truth_df = pd.read_excel(ground_truth_file, engine="openpyxl")

        if approach_df.empty:
            continue

        # Check for inconsistencies in the data
        for i, row in approach_df.iterrows():
            constraint_correctness = row["constraint_correctness"]
            tp = row["tp"]
            print(constraint_correctness, tp)
            if constraint_correctness == "FP" and tp == 1:
                print(f"Line {i}: Error: FP but tp == 1")
                input()  # Pause for user to acknowledge the error

        # Calculate basic metrics
        total = len(approach_df)
        total_tp = approach_df[
            approach_df["tp"] == 1
        ]  # True positives with correct script
        total_correct = len(total_tp)

        # Calculate accuracy
        accuracy = total_correct / total if total > 0 else 0
        accuracy_pct = round(accuracy * 100, 1)

        # Apply verification filter
        filter_df = approach_df[approach_df["verify_result"] != 0]
        filter_total = len(filter_df)
        filter_tp = filter_df[filter_df["tp"] == 1]
        filter_correct = len(filter_tp)

        # Calculate filtered accuracy
        filter_accuracy = filter_correct / filter_total if filter_total > 0 else 0
        filter_accuracy_pct = round(filter_accuracy * 100, 1)

        # Prepare ground truth and approach data for comparison
        tmp_ground_truth_df = ground_truth_df.copy()
        tmp_ground_truth_df["concat"] = (
            tmp_ground_truth_df["attribute"]
            + tmp_ground_truth_df["description"]
            + tmp_ground_truth_df["operation"]
        )

        # Calculate false negatives for unfiltered results
        tmp_approach_df = total_tp.copy()
        tmp_approach_df["concat"] = (
            tmp_approach_df["attribute"]
            + tmp_approach_df["description"]
            + tmp_approach_df["operation"]
        )

        gt_values = set(tmp_ground_truth_df["concat"].values)
        approach_values = set(tmp_approach_df["concat"].values)
        fns = gt_values - approach_values

        # Calculate false negatives for filtered results
        tmp_approach_df = filter_tp.copy()
        tmp_approach_df["concat"] = (
            tmp_approach_df["attribute"]
            + tmp_approach_df["description"]
            + tmp_approach_df["operation"]
        )

        gt_values = set(tmp_ground_truth_df["concat"].values)
        approach_values = set(tmp_approach_df["concat"].values)
        fns_filter = gt_values - approach_values

        # Calculate recall and F1 for unfiltered results
        if len(fns) == 0:
            recall = "-"
            f1 = "-"
        else:
            if total_correct + len(fns) > 0:
                recall_val = total_correct / (total_correct + len(fns))
                recall = round(recall_val * 100, 1)

                if accuracy_pct + recall > 0:
                    f1 = 2 * (accuracy_pct * recall) / (accuracy_pct + recall)
                    f1 = round(f1, 1)
                else:
                    f1 = 0.0
            else:
                recall = 0.0
                f1 = 0.0

        # Calculate recall and F1 for filtered results
        if len(fns_filter) == 0:
            filter_recall = "-"
            filter_f1 = "-"
        else:
            if filter_correct + len(fns_filter) > 0:
                filter_recall_val = filter_correct / (filter_correct + len(fns_filter))
                filter_recall = round(filter_recall_val * 100, 1)

                if filter_accuracy_pct + filter_recall > 0:
                    filter_f1 = (
                        2
                        * (filter_accuracy_pct * filter_recall)
                        / (filter_accuracy_pct + filter_recall)
                    )
                    filter_f1 = round(filter_f1, 1)
                else:
                    filter_f1 = 0.0
            else:
                filter_recall = 0.0
                filter_f1 = 0.0

        # Append results to output CSV
        with open(csv_file_path, "a") as f:
            f.write(
                f"{api_folder},{CONSTRAINT_TYPE},{total},{total_correct},{accuracy_pct},"
                f"{len(fns)},{recall},{f1},{filter_total},{filter_correct},"
                f"{filter_accuracy_pct},{len(fns_filter)},{filter_recall},{filter_f1}\n"
            )

        # Create and store test generation result
        result = TestGenResults(
            api_name=api_folder,
            constraint_type=CONSTRAINT_TYPE,
            total_constraints=total,
            correct_constraints=total_correct,
            accuracy=accuracy_pct,
            false_negatives=len(fns),
            recall=recall,
            f1_score=f1,
            filtered_total=filter_total,
            filtered_correct=filter_correct,
            filtered_accuracy=filter_accuracy_pct,
            filtered_false_negatives=len(fns_filter),
            filtered_recall=filter_recall,
            filtered_f1_score=filter_f1,
        )
        results.append(result)

    return results


def save_category_statistics(
    approach_folder: Path, categories_dict: Dict[str, Dict[str, Union[str, int]]]
) -> None:
    """
    Save constraint category statistics to an Excel file.

    Args:
        approach_folder: Path to the folder containing approach results
        categories_dict: Dictionary mapping API names to category counts
    """
    categories_df = pd.DataFrame(categories_dict).transpose()

    # If the file already exists, append to it
    output_path = approach_folder / "categories.xlsx"
    if output_path.exists():
        tmp_df = pd.read_excel(output_path, engine="openpyxl")
        categories_df = pd.concat([tmp_df, categories_df])

    # Save to Excel
    categories_df.to_excel(output_path)


def main() -> None:
    """
    Main function to run the response property constraint evaluation.

    This function demonstrates how to use the evaluation functions
    with command-line arguments or default values.
    """
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Evaluate response property constraints")
    parser.add_argument(
        "--approach-folder",
        type=str,
        default="approaches/rbctest_our_data",
        help="Folder containing approach results",
    )
    parser.add_argument(
        "--ground-truth-folder",
        type=str,
        default="ground_truth",
        help="Folder containing ground truth data",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="evaluation_results.csv",
        help="Path for the output CSV file",
    )
    parser.add_argument(
        "--api-folders",
        type=str,
        nargs="+",
        help="API folders to evaluate (default: all)",
    )
    parser.add_argument(
        "--export", action="store_true", help="Export results to original files"
    )
    parser.add_argument(
        "--verifier", action="store_true", help="Apply verification filter"
    )

    args = parser.parse_args()

    # If API folders not specified, find all folders in the approach directory
    if not args.api_folders:
        approach_path = Path(args.approach_folder)
        args.api_folders = [
            folder.name
            for folder in approach_path.iterdir()
            if folder.is_dir() and folder.name != ".DS_Store"
        ]

    # Create evaluation configuration
    config = EvaluationConfig.from_paths(
        approach_folder=args.approach_folder,
        ground_truth_folder=args.ground_truth_folder,
        output_csv=args.output_csv,
        api_folders=args.api_folders,
        export_results=args.export,
        apply_verification_filter=args.verifier,
    )

    # Run the evaluations
    mining_results = evaluate_response_property_constraint_mining(config)
    test_gen_results = evaluate_response_property_test_gen(config)

    # Print summary
    for result in mining_results:
        print(
            f"{result.api_name}: Precision={result.precision}, Recall={result.recall}, F1={result.f1_score}"
        )


if __name__ == "__main__":
    main()
