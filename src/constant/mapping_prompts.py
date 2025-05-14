# /src/constant/mapping_prompts.py

"""
Mapping-related prompt constants used for mapping between parameters and schema attributes.
"""

PARAMETER_SCHEMA_MAPPING_PROMPT = """Given an input parameter and an API response schema, your responsibility is to check whether there is a corresponding attribute in the API response schema.

Below is the input parameter of the operation {method} {endpoint}:
- "{attribute}": "{description}"

Follow these step to find the coresponding attribute of the input parameter:
STEP 1: Let's give a brief observation about the input parameter.

{parameter_observation}

STEP 2: Identify the corresponding attribute in the API response's schema.

Some cases can help determine a corresponding attribute:
- The input parameter is used for filtering, and there is a corresponding attribute that reflects the real value (result of the filter); but this attribute must be in the same object as the input parameter.
- The input parameter and the corresponding attribute maintain the same semantic meaning regarding their values.

Below is the specification of the schema "{schema}":
{schema_observation}

If there is a corresponding attribute in the response schema, let's explain the identified attribute. Follow the format of triple backticks below:
```explanation
explain...
```

Let's give your confirmation: Does the input parameter have any corresponding attribute in the response schema? Follow the format of triple backticks below:
```answer
just respond: yes/no (without any explanation)
```

Let's identify all corresponding attributes name of the provided input parameter in {attributes}. Format of triple backticks below:
```corresponding attribute
just respond corresponding attribute's name here (without any explanation)
```
"""

NAIVE_PARAMETER_SCHEMA_MAPPING_PROMPT = """Given an input parameter and an API response schema, your responsibility is to check whether there is a corresponding attribute in the API response schema.

Below is the input parameter of the operation {method} {endpoint}:
- "{attribute}": "{description}"

Follow these step to find the coresponding attribute of the input parameter:


Identify the corresponding attribute in the API response's schema.

Some cases can help determine a corresponding attribute:
- The input parameter is used for filtering, and there is a corresponding attribute that reflects the real value (result of the filter); but this attribute must be in the same object as the input parameter.
- The input parameter and the corresponding attribute maintain the same semantic meaning regarding their values.

Below is the specification of the schema "{schema}":
{schema_specification}

If there is a corresponding attribute in the response schema, let's explain the identified attribute. Follow the format of triple backticks below:
```explanation
explain...
```

Let's give your confirmation: Does the input parameter have any corresponding attribute in the response schema? Follow the format of triple backticks below:
```answer
just respond: yes/no (without any explanation)
```

Let's identify all corresponding attributes name of the provided input parameter in {attributes}. Format of triple backticks below:
```corresponding attribute
just respond corresponding attribute's name here (without any explanation)
```
"""

MAPPING_CONFIRMATION = """Given an input parameter of a REST API and an identified equivalent attribute in an API response schema, your responsibility is to check that the mapping is correct.

The input parameter's information:
- Operation: {method} {endpoint}
- Parameter: "{parameter_name}"
- Description: "{description}"

The corresponding attribute's information:
- Resource: {schema}
- Corresponding attribute: "{corresponding_attribute}"

STEP 1, determine the equivalence of resources based on the operation, the description of the input parameter. Explain about the resource of the input parameter, follow the format of triple backticks below:
```explanation
your explanation...
```

STEP 2, based on your explanation about the provided input parameter's resource, help to check the mapping of the input parameter as "{parameter_name}" with the equivalent attribute as "{corresponding_attribute}" specified in the {schema} resource.

Note that: The mapping is correct if their values are related to a specific attribute of a resource or their semantics are equivalent.

The last response should follow the format of triple backticks below:
```answer
just respond: correct/incorrect
```
"""

DATA_MODEL_PROMPT = r"""Given two schemas specified in an OpenAPI Specification file, your responsibility is to find all pairs of two fields that have the same meaning.

Below are the two schemas needed to find pairs:
Schema 1: {schema_1}
Schema 2: {schema_2}

Rules:
1. The two fields in a pair must be of the same data type.
2. The two fields in a pair must share the same meaning; their values should represent the id of the same object or maintain an attribute value of the same object,...
3. A field in one schema only pairs with at most one field in another schema, and vice versa.

Please follow these rules in your response:
1. If there exist pairs of two fields that share the same meaning:
Follow the format below to indicate them:
<field at Schema 1> -> <field at Schema 2>
...
2. If there are no pairs of two fields with the same meaning found between the two schemas, you only need to respond with "None"."""
