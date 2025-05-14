"""
OpenAPI Example Finder Module

This module provides utilities for finding example values in OpenAPI specifications.
"""

import json
from typing import Dict, List, Any, Optional, Union, Tuple, TypeVar, cast
from pathlib import Path

from models.example_models import (
    ExampleSearchOptions,
    ExampleSearchResult,
)

# Type variables for recursive functions
T = TypeVar("T")
JsonDict = Dict[str, Any]


def find_key(
    obj: Union[Dict[str, Any], List[Any]],
    key: str,
    ancestor_key: str,
    within_ancestor: bool = False,
) -> Optional[Any]:
    """
    Recursively search for a key within a nested structure, optionally within a specific ancestor.

    Args:
        obj: The object to search through (dictionary or list)
        key: The key to search for
        ancestor_key: The ancestor key to restrict the search to
        within_ancestor: Whether we're currently within the ancestor's scope

    Returns:
        The value of the first matching key found, or None if not found
    """
    if within_ancestor:
        # Now we are within the ancestor_key, check if key exists
        if isinstance(obj, dict) and key in obj:
            return obj[key]

    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == ancestor_key:
                # Once the ancestor_key is found, search only within its scope
                if isinstance(v, dict):
                    result = find_key(v, key, ancestor_key, True)
                    if result is not None:
                        return result
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, dict):
                            result = find_key(item, key, ancestor_key, True)
                            if result is not None:
                                return result

            # Continue to search recursively in nested dictionaries and lists
            if isinstance(v, dict):
                result = find_key(v, key, ancestor_key, within_ancestor)
                if result is not None:
                    return result
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        result = find_key(item, key, ancestor_key, within_ancestor)
                        if result is not None:
                            return result
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                result = find_key(item, key, ancestor_key, within_ancestor)
                if result is not None:
                    return result

    return None


def find_keys(
    obj: Dict[str, Any], key: str, ancestor_key: str, within_ancestor: bool = False
) -> List[Any]:
    """
    Recursively search for all occurrences of a key within a nested structure.

    Args:
        obj: The dictionary to search through
        key: The key to search for
        ancestor_key: The ancestor key to restrict the search to
        within_ancestor: Whether we're currently within the ancestor's scope

    Returns:
        A list of all values found for the matching key
    """
    results: List[Any] = []

    if within_ancestor and key in obj:
        # Now we are within the ancestor_key, check if key exists
        results.append(obj[key])

    for k, v in obj.items():
        if k == ancestor_key:
            # Once the ancestor_key is found, search only within its scope
            if isinstance(v, dict):
                results.extend(find_keys(v, key, ancestor_key, True))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        results.extend(find_keys(item, key, ancestor_key, True))

        # Continue to search recursively in nested dictionaries and lists
        if isinstance(v, dict):
            results.extend(find_keys(v, key, ancestor_key, within_ancestor))
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    results.extend(
                        find_keys(
                            cast(Dict[str, Any], item),
                            key,
                            ancestor_key,
                            within_ancestor,
                        )
                    )

    return results


class OpenAPIExampleFinder:
    """
    A class for finding example values in OpenAPI specifications.

    This class provides methods to search for example values for specific fields
    in different parts of an OpenAPI specification.
    """

    def __init__(
        self,
        openapi_spec: Dict[str, Any],
        options: Optional[ExampleSearchOptions] = None,
    ):
        """
        Initialize the OpenAPIExampleFinder.

        Args:
            openapi_spec: Dictionary containing the OpenAPI specification
            options: Search options (defaults to ExampleSearchOptions())
        """
        self.openapi_spec = openapi_spec
        self.options = options or ExampleSearchOptions()

    def find_example_value(
        self, object_name: str, field_name: str
    ) -> ExampleSearchResult:
        """
        Find an example value for a field in an object using multiple search strategies.

        Args:
            object_name: The name of the object/schema containing the field
            field_name: The name of the field to find an example for

        Returns:
            An ExampleSearchResult containing the found example or information about the search
        """
        result = ExampleSearchResult(
            object_name=object_name,
            field_name=field_name,
            example_value=None,
            source="none",
            found=False,
        )

        # First check in OpenAPI 3.0 components
        if self.options.check_components:
            example_value = self._find_example_value_in_components(
                object_name, field_name
            )
            if example_value is not None:
                result.example_value = example_value
                result.source = "components"
                result.found = True
                return result

        # Next check in OpenAPI 2.0 definitions
        if self.options.check_definitions:
            example_value = self._find_example_value_in_definitions(
                object_name, field_name
            )
            if example_value is not None:
                result.example_value = example_value
                result.source = "definitions"
                result.found = True
                return result

        # Finally try a brute force approach
        if self.options.use_brute_force:
            example_value = self._find_example_value_brute_force(
                object_name, field_name
            )
            if example_value is not None:
                result.example_value = example_value
                result.source = "brute_force"
                result.found = True
                return result

        return result

    def _find_example_value_brute_force(
        self, object_name: str, field_name: str
    ) -> Optional[Any]:
        """
        Find an example value by searching throughout the entire spec.

        Args:
            object_name: The name of the object containing the field
            field_name: The name of the field to find an example for

        Returns:
            The example value if found, None otherwise
        """
        # First check if there's an example object with our field
        example_object = find_key(self.openapi_spec, "example", object_name)
        example_value = None

        if example_object is not None:
            example_value = find_key(example_object, field_name, "", True)

        if example_value is None:
            example_value = find_key(self.openapi_spec, field_name, "example")

        if example_value is not None:
            # Ensure the value is a primitive data type or list of primitives
            if isinstance(example_value, (str, int, float, bool)):
                return example_value
            elif isinstance(example_value, list):
                # Check if all items are primitives
                if all(
                    isinstance(item, (str, int, float, bool)) for item in example_value
                ):
                    return example_value

        return None

    def _find_example_value_in_definitions(
        self, object_name: str, field_name: str
    ) -> Optional[Any]:
        """
        Find an example value in OpenAPI 2.0 definitions.

        Args:
            object_name: The name of the object/schema containing the field
            field_name: The name of the field to find an example for

        Returns:
            The example value if found, None otherwise
        """
        # Get the definitions object
        definitions = self.openapi_spec.get("definitions", {})
        target_object = definitions.get(object_name, {})

        # First check for an example at the object level
        example = target_object.get("example", {})
        if isinstance(example, list) and len(example) > 0:
            for example_value in example:
                if example_value.get(field_name, None) is not None:
                    return example_value.get(field_name, None)
            example_value = None
        else:
            # Check for the field in the example object
            example_value = example.get(field_name, None)

        # Next check for an example at the property level
        if example_value is None:
            properties = target_object.get("properties", {})
            field = properties.get(field_name, {})
            example_value = field.get("example", None)

            # Check for enum values if configured and no example found
            if example_value is None and self.options.use_enum_values:
                enum_values = field.get("enum", [])
                if enum_values and len(enum_values) > 0:
                    return enum_values[0]

            # Check for default values if configured and no example found
            if example_value is None and self.options.use_default_values:
                default_value = field.get("default", None)
                if default_value is not None:
                    return default_value

        return example_value

    def _find_example_value_in_components(
        self, object_name: str, field_name: str
    ) -> Optional[Any]:
        """
        Find an example value in OpenAPI 3.0 components.

        Args:
            object_name: The name of the object/schema containing the field
            field_name: The name of the field to find an example for

        Returns:
            The example value if found, None otherwise
        """
        # Get the components.schemas object
        components = self.openapi_spec.get("components", {})
        schemas = components.get("schemas", {})
        target_object = schemas.get(object_name, {})

        # First check at the property level
        field = target_object.get("properties", {}).get(field_name, {})
        example_value = field.get("example", None)

        # Next check at the object level
        if example_value is None:
            example = target_object.get("example", {})
            if isinstance(example, list) and len(example) > 0:
                example_value = example[0].get(field_name, None)
            else:
                example_value = example.get(field_name, None)

        # Check for enum values if configured and no example found
        if example_value is None and self.options.use_enum_values:
            enum_values = field.get("enum", [])
            if enum_values and len(enum_values) > 0:
                return enum_values[0]

        # Check for default values if configured and no example found
        if example_value is None and self.options.use_default_values:
            default_value = field.get("default", None)
            if default_value is not None:
                return default_value

        return example_value


def load_openapi_spec(filepath: Union[str, Path]) -> Dict[str, Any]:
    """
    Load and parse an OpenAPI specification from a file.

    Args:
        filepath: Path to the OpenAPI specification file

    Returns:
        Dictionary containing the parsed OpenAPI specification

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file can't be parsed as JSON
    """
    filepath = Path(filepath) if isinstance(filepath, str) else filepath

    if not filepath.exists():
        raise FileNotFoundError(f"OpenAPI specification file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as file:
        openapi_spec = json.load(file)

    return openapi_spec
