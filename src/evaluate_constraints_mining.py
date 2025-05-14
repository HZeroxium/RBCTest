# /src/evaluate_constraints_mining.py

"""
Constraint Mining Evaluation Module

This module evaluates constraint mining approaches against ground truth data.
It provides functions to assess both request-response constraint mining and
response property constraint mining approaches.
"""

import os
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any

from models.evaluation_models import ConstraintEvaluationConfig
from eval.request_approach_evaluate import (
    evaluate_request_response_constraint_mining,
    evaluate_request_response_test_gen,
)
from eval.response_approach_evaluate import (
    evaluate_response_property_constraint_mining,
    evaluate_response_property_test_gen,
)


def evaluate_constraint_mining(config: ConstraintEvaluationConfig) -> Dict[str, Any]:
    """
    Evaluate constraint mining approaches against ground truth.

    Args:
        config: Configuration for constraint evaluation

    Returns:
        Dictionary containing evaluation results
    """
    # Initialize results dictionary
    results = {"response_property": {}, "request_response": {}}

    # Remove existing evaluation file if it exists
    if os.path.exists(config.output_csv_path):
        os.remove(config.output_csv_path)

    # Make a copy of the configuration for request-response evaluation
    request_config = ConstraintEvaluationConfig(
        approach_folder=config.approach_folder,
        ground_truth_folder=config.ground_truth_folder,
        api_folders=config.api_folders,
        output_csv_path=config.output_csv_path,
        export=config.export,
        verifier=config.verifier,
    )

    # Evaluate request-response constraint mining
    req_res_results = evaluate_request_response_constraint_mining(
        config.approach_folder,
        config.ground_truth_folder,
        config.api_folders,
        config.output_csv_path,
        verifier=config.verifier,
        export=config.export,
    )

    if req_res_results:
        results["request_response"] = req_res_results

    # Evaluate response property constraint mining
    resp_prop_results = evaluate_response_property_constraint_mining(
        config.approach_folder,
        config.ground_truth_folder,
        config.api_folders,
        config.output_csv_path,
        verifier=config.verifier,
        export=config.export,
    )

    if resp_prop_results:
        results["response_property"] = resp_prop_results

    return results


def evaluate_test_generation(config: ConstraintEvaluationConfig) -> Dict[str, Any]:
    """
    Evaluate test generation approaches.

    Args:
        config: Configuration for test generation evaluation

    Returns:
        Dictionary containing evaluation results
    """
    # Initialize results dictionary
    results = {"response_property": {}, "request_response": {}}

    # Configure output path for test generation evaluation
    test_gen_csv_path = config.output_csv_path.replace(".csv", "_test_gen__.csv")

    # Remove existing evaluation file if it exists
    if os.path.exists(test_gen_csv_path):
        os.remove(test_gen_csv_path)

    # Evaluate request-response test generation
    req_res_gen_results = evaluate_request_response_test_gen(
        config.approach_folder,
        config.api_folders,
        test_gen_csv_path,
        config.ground_truth_folder,
    )

    if req_res_gen_results:
        results["request_response"] = req_res_gen_results

    # Evaluate response property test generation
    resp_prop_gen_results = evaluate_response_property_test_gen(
        config.approach_folder,
        config.api_folders,
        test_gen_csv_path,
        config.ground_truth_folder,
    )

    if resp_prop_gen_results:
        results["response_property"] = resp_prop_gen_results

    # Read and analyze resulting CSV file if it exists
    if os.path.exists(test_gen_csv_path):
        try:
            test_gen_df = pd.read_csv(test_gen_csv_path)
            results["summary"] = {
                "total_apis": len(test_gen_df["API"].unique()),
                "total_constraints": len(test_gen_df),
                "average_accuracy": (
                    test_gen_df["accuracy"].mean()
                    if "accuracy" in test_gen_df.columns
                    else None
                ),
                "average_recall": (
                    test_gen_df["recall"].mean()
                    if "recall" in test_gen_df.columns
                    else None
                ),
                "average_f1": (
                    test_gen_df["f1"].mean() if "f1" in test_gen_df.columns else None
                ),
            }
        except Exception as e:
            print(f"Error analyzing test generation CSV: {e}")

    return results


def main() -> None:
    """
    Main entry point for evaluating constraint mining and test generation.

    This function sets up the evaluation configuration and runs both
    constraint mining evaluation and test generation evaluation.
    """
    # Configure the evaluation
    approach_folder = "approaches/baseline"
    ground_truth_folder = "approaches/ground_truth"
    csv_file = f"{approach_folder}/approach_evaluation.csv"

    # Get API folders
    api_folders = [
        f
        for f in os.listdir(ground_truth_folder)
        if not f.startswith(".") and os.path.isdir(os.path.join(ground_truth_folder, f))
    ]
    api_folders.sort()

    # Create evaluation configuration for constraint mining
    eval_config = ConstraintEvaluationConfig(
        approach_folder=approach_folder,
        ground_truth_folder=ground_truth_folder,
        api_folders=api_folders,
        output_csv_path=csv_file,
        export=True,
        verifier=False,
    )

    print("\n=== Evaluating Constraint Mining ===")
    # Run constraint mining evaluation
    mining_results = evaluate_constraint_mining(eval_config)

    # Print constraint mining evaluation summary
    if mining_results:
        print("\nConstraint Mining Evaluation Summary:")
        for constraint_type, results in mining_results.items():
            print(f"\n{constraint_type.replace('_', ' ').title()}:")
            for key, value in results.items():
                print(f"  {key}: {value}")

    # Update API folders for test generation evaluation (might have changed)
    test_gen_api_folders = [
        f
        for f in os.listdir(approach_folder)
        if not f.startswith(".") and os.path.isdir(os.path.join(approach_folder, f))
    ]
    test_gen_api_folders.sort()

    # Create test generation evaluation configuration
    test_gen_config = ConstraintEvaluationConfig(
        approach_folder=approach_folder,
        ground_truth_folder=ground_truth_folder,
        api_folders=test_gen_api_folders,
        output_csv_path=csv_file,
        export=True,
        verifier=False,
    )

    print("\n=== Evaluating Test Generation ===")
    # Run test generation evaluation
    test_gen_results = evaluate_test_generation(test_gen_config)

    # Print test generation evaluation summary
    if test_gen_results and "summary" in test_gen_results:
        print("\nTest Generation Evaluation Summary:")
        for key, value in test_gen_results["summary"].items():
            print(f"  {key}: {value}")

    print("\nEvaluation complete. Results saved to CSV files.")


if __name__ == "__main__":
    main()
