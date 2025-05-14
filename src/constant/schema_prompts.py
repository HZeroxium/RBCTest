"""
Schema-related prompt constants used for understanding API schemas.
"""

SCHEMA_OBSERVATION = """\
Given a schema in an OpenAPI Specification for a RESTful API service, your responsibility is to briefly explain the meaning of each attribute specified in the provided schema.

Below is the schema's specification:
- Schema name: "{schema}"
- Specification: {specification}
"""

FIND_SCHEMA_KEYS = """Given a schema in an OpenAPI specification file, your responsibility is to identify one or some attributes in the schema that play the role of identifying the specific object (primary keys):

Below is the schema specification:
{schema_specification}

If the given schema does not reflect an object, you only need to respond with "None"; otherwise, respond with the primary keys you identified, separated by commas. No explanation is needed."""
