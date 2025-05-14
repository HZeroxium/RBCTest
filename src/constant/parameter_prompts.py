# /src/constant/parameter_prompts.py

"""
Parameter-related prompt constants used for understanding API parameters.
"""

PARAMETER_OBSERVATION = """Given the specification of an input parameter for a REST API, your responsibility is to provide a brief observation of that parameter.

Below is the input parameter of the operation {method} {endpoint}:
- "{attribute}": "{description}"
"""
