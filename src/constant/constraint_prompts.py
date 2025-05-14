# /src/constant/constraint_prompts.py

"""
Constraint-related prompt constants used for detecting and confirming constraints.
"""

DESCRIPTION_OBSERVATION_PROMPT = """Given a description of an attribute in an OpenAPI Specification, your responsibility is to identify whether the description implies any constraints, rules, or limitations for legalizing the attribute itself.

Below is the attribute's specification:
- name: "{attribute}"
- type: {data_type}
- description: "{description}"
- schema: "{param_schema}"

If the description implies any constraints, rules, or limitations for legalizing the attribute itself, let's provide a brief description of these constraints.
"""

NAIVE_CONSTRAINT_DETECTION_PROMPT = """Given a description of an attribute in an OpenAPI Specification, your responsibility is to identify whether the description implies any constraints, rules, or limitations for legalizing the attribute itself.

Below is the attribute's specification:
- name: "{attribute}"
- type: {data_type}
- description: "{description}"

If the description implies any constraints, rules, or limitations for legalizing the attribute itself, return yes; otherwise, return no. follow the following format:
```answer
yes/no
```
"""

CONSTRAINT_CONFIRMATION = """Given a description of an attribute in an OpenAPI Specification, your responsibility is to identify whether the description implies any constraints, rules, or limitations for legalizing the attribute itself. Ensure that the description contains sufficient information to generate a script capable of verifying these constraints.

Below is the attribute's specification:
- name: "{attribute}"
- type: {data_type}
- description: "{description}"
- schema: "{param_schema}"

Does the description imply any constraints, rules, or limitations?
- {description_observation}

Follow these rules to identify the capability of generating a constraint validation test script:
- If there is a constraint for the attribute itself, check if the description contains specific predefined values, ranges, formats, etc. Exception: Predefined values such as True/False for the attribute whose data type is boolean are not good constraints.
- If there is an inter-parameter constraint, ensure that the relevant attributes have been mentioned in the description.

Now, let's confirm: Is there sufficient information mentioned in the description to generate a script for verifying these identified constraints?
```answer
yes/no
```
"""
