# /src/eval/eval_invariants.py


"""
Invariant Evaluation GUI Application

This module provides a graphical user interface for evaluating invariants stored in a CSV file.
Users can navigate through the invariants, view their details, and mark them as true ('t') or false ('f').
"""

import pandas as pd
import tkinter as tk
from tkinter import messagebox, scrolledtext
from pathlib import Path
from typing import Optional

from models.evaluation_models import InvariantRecord, InvariantEvaluatorConfig


class InvariantEvaluator:
    """
    A GUI application for evaluating invariants stored in a CSV file.

    This class provides an interface for navigating through invariants,
    viewing their details, and marking each as true ('t') or false ('f').
    """

    def __init__(self, config: InvariantEvaluatorConfig):
        """
        Initialize the invariant evaluator application.

        Args:
            config: Configuration parameters for the evaluator
        """
        self.config = config
        self.current_index = 0
        self.load_data()
        self.create_ui()

    def load_data(self) -> None:
        """
        Load invariant data from the configured CSV file.

        If the 'eval' column doesn't exist in the file, it will be added.
        """
        try:
            self.df = pd.read_csv(
                self.config.csv_file,
                encoding=self.config.encoding,
                sep=self.config.separator,
            )
            print(self.df.head())

            # Add 'eval' column if it does not exist
            if "eval" not in self.df.columns:
                self.df["eval"] = ""
        except Exception as e:
            messagebox.showerror("Error Loading CSV", f"Failed to load CSV file: {e}")
            raise

    def create_ui(self) -> None:
        """
        Create the user interface for the invariant evaluator.

        This sets up all the necessary tkinter components including:
        - Frames for layout
        - Labels for headings
        - Text boxes for displaying invariant details
        - Entry field for evaluation input
        - Navigation and save buttons
        """
        # Create the main application window
        self.root = tk.Tk()
        self.root.title("Invariant Evaluator")
        self.root.geometry(
            f"{self.root.winfo_screenwidth()}x{self.root.winfo_screenheight()}"
        )

        # Define UI elements
        self.create_header_section()
        self.create_invariant_details_section()
        self.create_assertion_section()
        self.create_input_section()
        self.create_navigation_buttons()

        # Update the UI with initial data
        self.update_ui()

    def create_header_section(self) -> None:
        """Create the header section with row counter."""
        self.label_frame = tk.Frame(self.root)
        self.label_frame.pack(pady=20)

        # Label to show the index of the current row
        self.index_label = tk.Label(
            self.label_frame,
            text=f"Row {self.current_index + 1} of {len(self.df)}",
            font=(self.config.font_family, 30, "bold"),
            fg="red",
        )
        self.index_label.pack()

    def create_invariant_details_section(self) -> None:
        """Create the section for displaying invariant details."""
        self.upper_frame = tk.Frame(self.root)
        self.upper_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Upper section for displaying "Invariant Details"
        self.upper_label = tk.Label(
            self.upper_frame,
            text="Invariant Details",
            font=(self.config.font_family, 20, "bold"),
            fg="blue",
        )
        self.upper_label.pack()

        self.upper_textbox = scrolledtext.ScrolledText(
            self.upper_frame,
            wrap=tk.WORD,
            height=10,
            font=(self.config.font_family, 16, "normal"),
        )
        self.upper_textbox.pack(fill=tk.BOTH, expand=True)

    def create_assertion_section(self) -> None:
        """Create the section for displaying Postman assertion and description."""
        self.lower_frame = tk.Frame(self.root)
        self.lower_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Lower section for displaying "Postman Assertion and Description"
        self.lower_label = tk.Label(
            self.lower_frame,
            text="Postman Assertion and Description",
            font=(self.config.font_family, 20, "bold"),
            fg="blue",
        )
        self.lower_label.pack()

        self.lower_textbox = scrolledtext.ScrolledText(
            self.lower_frame,
            wrap=tk.WORD,
            height=10,
            font=(self.config.font_family, 16, "normal"),
        )
        self.lower_textbox.pack(fill=tk.BOTH, expand=True)

    def create_input_section(self) -> None:
        """Create the input section for evaluation entries."""
        # Input field for evaluation
        self.input_text = tk.StringVar()
        self.entry = tk.Entry(
            self.root,
            textvariable=self.input_text,
            font=(self.config.font_family, 20),
            width=50,
        )
        self.entry.pack(pady=20)
        self.entry.bind("<Return>", lambda event: self.navigate(1))

    def create_navigation_buttons(self) -> None:
        """Create navigation and save buttons."""
        self.button_frame = tk.Frame(self.root)
        self.button_frame.pack(pady=20)

        self.prev_button = tk.Button(
            self.button_frame, text="Previous", command=lambda: self.navigate(-1)
        )
        self.prev_button.pack(side=tk.LEFT, padx=5)

        self.next_button = tk.Button(
            self.button_frame, text="Next", command=lambda: self.navigate(1)
        )
        self.next_button.pack(side=tk.RIGHT, padx=5)

        self.save_button = tk.Button(self.root, text="Save", command=self.save_input)
        self.save_button.pack(pady=10)

    def update_ui(self) -> None:
        """
        Update UI elements with data from the current record.

        This method populates the text boxes with invariant details,
        postman assertion and description from the current record.
        """
        row_data = self.df.iloc[self.current_index].drop("eval").to_dict()

        # Create invariant record
        invariant = InvariantRecord(
            pptname=row_data["pptname"],
            invariant=row_data["invariant"],
            invariantType=row_data["invariantType"],
            variables=row_data["variables"],
            postmanAssertion=row_data["postmanAssertion"],
            description=row_data["description"],
            eval=self.df.at[self.current_index, "eval"],
        )

        # Format the text for the upper textbox
        upper_text = (
            f"{invariant.pptname}\n\n"
            f"{invariant.invariant}\n"
            f" - Type: {invariant.invariantType}\n"
            f" - Variables: {invariant.variables}"
        )

        # Format the text for the lower textbox
        lower_text = f"{invariant.postmanAssertion}\n\n" f"{invariant.description}"

        # Update the textboxes and input field
        self.upper_textbox.delete("1.0", tk.END)
        self.upper_textbox.insert(tk.INSERT, upper_text)

        self.lower_textbox.delete("1.0", tk.END)
        self.lower_textbox.insert(tk.INSERT, lower_text)

        self.input_text.set(invariant.eval)
        self.index_label.config(text=f"Row {self.current_index + 1} of {len(self.df)}")

    def navigate(self, direction: int) -> None:
        """
        Navigate to a different record in the dataframe.

        Args:
            direction: The direction to navigate (1 for next, -1 for previous)
        """
        self.save_input()
        new_index = self.current_index + direction

        if 0 <= new_index < len(self.df):
            self.current_index = new_index
            self.update_ui()
        else:
            messagebox.showwarning(
                "Navigation Error", "No more rows in that direction."
            )

        # Save the dataframe to the CSV file after navigation
        self.save_to_csv()

    def save_input(self) -> None:
        """
        Save the current evaluation input to the dataframe.

        Validates that the input is either 't' or 'f'.
        """
        eval_value = self.input_text.get().strip().lower()

        if eval_value in ["t", "f"]:
            self.df.at[self.current_index, "eval"] = eval_value
        else:
            messagebox.showerror(
                "Input Error", "Please enter 't' or 'f' for evaluation."
            )

    def save_to_csv(self) -> None:
        """Save the dataframe to the CSV file."""
        try:
            self.df.to_csv(
                self.config.csv_file,
                sep=self.config.separator,
                encoding=self.config.output_encoding,
                index=False,
            )
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save CSV file: {e}")

    def run(self) -> None:
        """Run the application main loop."""
        self.root.mainloop()
        # Make sure to save the dataframe when the application closes
        self.save_to_csv()


def main() -> None:
    """Main entry point for the invariant evaluator application."""
    # Define the CSV file path
    csv_file = Path("experiment_our/Hotel Search API/invariants_description.csv")

    # Create the configuration
    config = InvariantEvaluatorConfig.from_path(str(csv_file))

    # Create and run the evaluator
    evaluator = InvariantEvaluator(config)
    evaluator.run()


if __name__ == "__main__":
    main()
