# Prompt Constants

This directory contains prompt templates used throughout the RBCTest project. These prompts are designed for interaction with language models to perform various tasks related to API testing and verification.

## Files Organization

- `parameter_prompts.py` - Prompts related to API parameter analysis
- `schema_prompts.py` - Prompts related to API schema understanding
- `mapping_prompts.py` - Prompts for mapping between parameters and schema attributes
- `constraint_prompts.py` - Prompts for detecting and confirming constraints
- `verification_prompts.py` - Prompts for generating verification scripts
- `data_model_prompts.py` - Prompts for building data models

## Usage

Import the prompts directly from their respective modules:

```python
from constant.parameter_prompts import PARAMETER_OBSERVATION
from constant.schema_prompts import SCHEMA_OBSERVATION
from constant.mapping_prompts import PARAMETER_SCHEMA_MAPPING_PROMPT
from constant.constraint_prompts import DESCRIPTION_OBSERVATION_PROMPT
from constant.verification_prompts import GROOVY_SCRIPT_VERIFICATION_GENERATION_PROMPT
```
