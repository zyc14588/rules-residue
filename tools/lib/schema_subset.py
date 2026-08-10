from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


def _matches_type(instance: Any, expected: str) -> bool:
    if expected == "null":
        return instance is None
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "object":
        return isinstance(instance, dict)
    return False


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if "const" in schema and instance != schema["const"]:
        issues.append(ValidationIssue(path, f"must equal {schema['const']!r}"))
        return issues

    if "enum" in schema and instance not in schema["enum"]:
        issues.append(ValidationIssue(path, f"must be one of {schema['enum']!r}"))
        return issues

    expected_type = schema.get("type")
    if expected_type is not None:
        allowed = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_matches_type(instance, item) for item in allowed):
            issues.append(ValidationIssue(path, f"expected type {allowed!r}"))
            return issues

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                issues.append(ValidationIssue(path, f"missing required property {key!r}"))

        properties = schema.get("properties", {})
        for key, value in instance.items():
            child_path = f"{path}.{key}"
            if key in properties:
                issues.extend(validate(value, properties[key], child_path))
                continue
            additional = schema.get("additionalProperties", True)
            if additional is False:
                issues.append(ValidationIssue(child_path, "additional property is not allowed"))
            elif isinstance(additional, dict):
                issues.extend(validate(value, additional, child_path))

    if isinstance(instance, list):
        minimum = schema.get("minItems")
        maximum = schema.get("maxItems")
        if minimum is not None and len(instance) < minimum:
            issues.append(ValidationIssue(path, f"must contain at least {minimum} items"))
        if maximum is not None and len(instance) > maximum:
            issues.append(ValidationIssue(path, f"must contain at most {maximum} items"))
        if schema.get("uniqueItems"):
            rendered = [repr(item) for item in instance]
            if len(rendered) != len(set(rendered)):
                issues.append(ValidationIssue(path, "items must be unique"))
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                issues.extend(validate(item, item_schema, f"{path}[{index}]"))

    if isinstance(instance, str):
        minimum = schema.get("minLength")
        maximum = schema.get("maxLength")
        if minimum is not None and len(instance) < minimum:
            issues.append(ValidationIssue(path, f"length must be >= {minimum}"))
        if maximum is not None and len(instance) > maximum:
            issues.append(ValidationIssue(path, f"length must be <= {maximum}"))
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, instance) is None:
            issues.append(ValidationIssue(path, f"does not match pattern {pattern!r}"))

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and instance < minimum:
            issues.append(ValidationIssue(path, f"must be >= {minimum}"))
        if maximum is not None and instance > maximum:
            issues.append(ValidationIssue(path, f"must be <= {maximum}"))

    alternatives = schema.get("oneOf")
    if isinstance(alternatives, list):
        matches = sum(1 for alternative in alternatives if not validate(instance, alternative, path))
        if matches != 1:
            issues.append(ValidationIssue(path, f"must match exactly one oneOf branch; matched {matches}"))

    return issues
