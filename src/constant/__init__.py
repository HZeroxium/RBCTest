"""
Constants package for prompt templates used in the RBCTest project.

This module exports all prompt constants from the various prompt modules.
"""

# Schema-related prompts
from .schema_prompts import SCHEMA_OBSERVATION, FIND_SCHEMA_KEYS

# Parameter-related prompts
from .parameter_prompts import PARAMETER_OBSERVATION

# Mapping-related prompts
from .mapping_prompts import (
    PARAMETER_SCHEMA_MAPPING_PROMPT,
    NAIVE_PARAMETER_SCHEMA_MAPPING_PROMPT,
    MAPPING_CONFIRMATION,
    DATA_MODEL_PROMPT,
)

# Constraint-related prompts
from .constraint_prompts import (
    DESCRIPTION_OBSERVATION_PROMPT,
    NAIVE_CONSTRAINT_DETECTION_PROMPT,
    CONSTRAINT_CONFIRMATION,
)

# Verification-related prompts
from .verification_prompts import (
    GROOVY_SCRIPT_VERIFICATION_GENERATION_PROMPT,
    IDL_TRANSFORMATION_PROMPT,
    CONST_INSIDE_RESPONSEBODY_SCRIPT_GEN_PROMPT,
    CONST_INSIDE_RESPONSEBODY_SCRIPT_CONFIRM_PROMPT,
    CONST_RESPONSEBODY_PARAM_SCRIPT_GEN_PROMPT,
    CONST_RESPONSEBODY_PARAM_SCRIPT_CONFIRM_PROMPT,
)

# Execution-related prompts
from .execution_prompts import (
    EXECUTION_SCRIPT,
    INPUT_PARAM_EXECUTION_SCRIPT,
    TEST_EXECUTION_SCRIPT,
    TEST_INPUT_PARAM_EXECUTION_SCRIPT,
)
