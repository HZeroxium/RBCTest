# /src/evaluate_test_gen.py

"""
Test Generation Evaluation Module

This module evaluates and categorizes test generation results.
It provides functions to categorize constraints and summarize test generation results.
"""

import os
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any

from utils.evaluation_utils import categorize_constraint, summarize_test_gen_response
from models.evaluation_models import (
    TestGenEvaluationConfig,
    TestGenSummary,
    CategoryStats,
)


def evaluate_and_summarize_test_gen(config: TestGenEvaluationConfig) -> TestGenSummary:
    """
    Evaluate and summarize test generation results.

    Args:
        config: Configuration for test generation evaluation

    Returns:
        TestGenSummary object containing evaluation results
    """
    # Initialize dictionaries for storing summaries
    summarize_test_gen_for_response: Dict[str, Dict[str, int]] = {}
    summarize_test_gen_for_request: Dict[str, Dict[str, int]] = {}
    api_names: List[str] = []
    all_true_mismatched = pd.DataFrame()

    # Create a TestGenSummary object to return
    summary = TestGenSummary()

    # Get list of API folders
    apis = [
        api
        for api in os.listdir(config.root_experiment_folder)
        if os.path.isdir(os.path.join(config.root_experiment_folder, api))
        and not api.startswith(".")
    ]
    apis.sort()

    # Process each API folder
    for api in apis:
        api_name = api.replace(" API", "")
        api_names.append(api_name)
        api_path = os.path.join(config.root_experiment_folder, api)

        # Find Excel files for constraints
        response_excel = os.path.join(api_path, "response_property_constraints.xlsx")
        request_excel = os.path.join(api_path, "request_response_constraints.xlsx")

        print(f"API: {api}")
        print(f"Found files: {response_excel}, {request_excel}")

        # Categorize constraints if knowledge base file is provided
        if config.knowledge_base_file and os.path.exists(config.knowledge_base_file):
            if os.path.exists(response_excel):
                categorize_constraint(response_excel, config.knowledge_base_file)
            if os.path.exists(request_excel):
                categorize_constraint(request_excel, config.knowledge_base_file)

        # Summarize response property constraints
        if os.path.exists(response_excel):
            summarize_test_gen_for_response, true_mismatched = (
                summarize_test_gen_response(
                    response_excel, summarize_test_gen_for_response, api_name
                )
            )
            all_true_mismatched = pd.concat([all_true_mismatched, true_mismatched])

            # Add to summary object
            category_stats = CategoryStats(
                all_count=summarize_test_gen_for_response[api_name]["All"],
                no_test_gen_count=summarize_test_gen_for_response[api_name][
                    "No test gen"
                ],
                correct_count=summarize_test_gen_for_response[api_name]["correct"],
                tp_satisfied_count=summarize_test_gen_for_response[api_name][
                    "TP_satisfied"
                ],
                tp_mismatched_count=summarize_test_gen_for_response[api_name][
                    "TP_mismatched"
                ],
                unknown_count=summarize_test_gen_for_response[api_name]["unknown"],
            )
            summary.api_stats[f"{api_name}_response"] = category_stats

        # Summarize request-response constraints
        if os.path.exists(request_excel):
            summarize_test_gen_for_request, true_mismatched = (
                summarize_test_gen_response(
                    request_excel, summarize_test_gen_for_request, api_name
                )
            )
            all_true_mismatched = pd.concat([all_true_mismatched, true_mismatched])

            # Add to summary object
            category_stats = CategoryStats(
                all_count=summarize_test_gen_for_request[api_name]["All"],
                no_test_gen_count=summarize_test_gen_for_request[api_name][
                    "No test gen"
                ],
                correct_count=summarize_test_gen_for_request[api_name]["correct"],
                tp_satisfied_count=summarize_test_gen_for_request[api_name][
                    "TP_satisfied"
                ],
                tp_mismatched_count=summarize_test_gen_for_request[api_name][
                    "TP_mismatched"
                ],
                unknown_count=summarize_test_gen_for_request[api_name]["unknown"],
            )
            summary.api_stats[f"{api_name}_request"] = category_stats

    # Calculate totals for response property constraints
    total_response = calculate_totals(summarize_test_gen_for_response, api_names)
    summarize_test_gen_for_response["Total"] = total_response

    # Add total response stats to summary
    summary.total_stats.all_count += total_response["All"]
    summary.total_stats.no_test_gen_count += total_response["No test gen"]
    summary.total_stats.correct_count += total_response["correct"]
    summary.total_stats.tp_satisfied_count += total_response["TP_satisfied"]
    summary.total_stats.tp_mismatched_count += total_response["TP_mismatched"]
    summary.total_stats.unknown_count += total_response["unknown"]

    # Calculate totals for request-response constraints
    total_request = calculate_totals(summarize_test_gen_for_request, api_names)
    summarize_test_gen_for_request["Total"] = total_request

    # Add total request stats to summary
    summary.total_stats.all_count += total_request["All"]
    summary.total_stats.no_test_gen_count += total_request["No test gen"]
    summary.total_stats.correct_count += total_request["correct"]
    summary.total_stats.tp_satisfied_count += total_request["TP_satisfied"]
    summary.total_stats.tp_mismatched_count += total_request["TP_mismatched"]
    summary.total_stats.unknown_count += total_request["unknown"]

    # Save results to Excel file
    save_summary_to_excel(
        config.output_file,
        summarize_test_gen_for_response,
        summarize_test_gen_for_request,
        all_true_mismatched,
    )

    return summary


def calculate_totals(
    summary_dict: Dict[str, Dict[str, int]], api_names: List[str]
) -> Dict[str, int]:
    """
    Calculate totals across all APIs for a summary dictionary.

    Args:
        summary_dict: Dictionary containing summaries for each API
        api_names: List of API names

    Returns:
        Dictionary containing total counts
    """
    total = {
        "All": 0,
        "No test gen": 0,
        "correct": 0,
        "TP_satisfied": 0,
        "TP_mismatched": 0,
        "unknown": 0,
    }

    for api in api_names:
        if api not in summary_dict:
            summary_dict[api] = {
                "All": 0,
                "No test gen": 0,
                "correct": 0,
                "TP_satisfied": 0,
                "TP_mismatched": 0,
                "unknown": 0,
            }
        else:
            for key in summary_dict[api]:
                if key in total:
                    total[key] += summary_dict[api][key]

    return total


def save_summary_to_excel(
    output_file: str,
    response_summary: Dict[str, Dict[str, int]],
    request_summary: Dict[str, Dict[str, int]],
    true_mismatched_df: pd.DataFrame,
) -> None:
    """
    Save summary results to an Excel file.

    Args:
        output_file: Path to the output Excel file
        response_summary: Summary of response property constraints
        request_summary: Summary of request-response constraints
        true_mismatched_df: DataFrame of mismatched constraints

    Returns:
        None
    """
    with pd.ExcelWriter(output_file) as writer:
        # Save response property summary
        df_response = pd.DataFrame.from_dict(response_summary, orient="index")
        df_response.sort_index(inplace=True)
        df_response.to_excel(writer, sheet_name="response")

        # Save request-response summary
        df_request = pd.DataFrame.from_dict(request_summary, orient="index")
        df_request.sort_index(inplace=True)
        df_request.to_excel(writer, sheet_name="request")

        # Save true mismatched constraints
        if not true_mismatched_df.empty:
            true_mismatched_df.to_excel(writer, sheet_name="all_true_mismatched")

    print(f"Summary saved to {output_file}")


def main() -> None:
    """
    Main entry point for evaluating test generation.

    This function sets up the evaluation configuration and runs the
    test generation evaluation and summarization.
    """
    # Configure the evaluation
    config = TestGenEvaluationConfig(
        root_experiment_folder="approaches/rbctest_our_data",
        output_file="approaches/rbctest_our_data/test_gen_summary.xlsx",
        knowledge_base_file=None,
    )

    # Run the evaluation and get summary
    summary = evaluate_and_summarize_test_gen(config)

    # Print summary statistics
    print("\nTest Generation Summary:")
    print(f"Total constraints: {summary.total_stats.all_count}")
    print(f"Correct test generations: {summary.total_stats.correct_count}")
    print(f"Satisfied constraints: {summary.total_stats.tp_satisfied_count}")
    print(f"Mismatched constraints: {summary.total_stats.tp_mismatched_count}")
    print(f"Unknown status: {summary.total_stats.unknown_count}")
    print("Done!")


if __name__ == "__main__":
    main()
