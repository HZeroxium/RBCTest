# /src/utils/common.py

from typing import List


def load_file_lines(file_path: str) -> List[str]:
    """
    Load lines from a file and strip whitespace.

    Args:
        file_path: Path to the file to be loaded

    Returns:
        List of stripped lines from the file
    """
    with open(file_path) as f:
        lines = f.readlines()
    return [line.strip() for line in lines]
