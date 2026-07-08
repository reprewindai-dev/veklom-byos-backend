"""Pydantic-based validation layer for TOOL_MAP call parameters."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError, create_model

# Registry: tool_name -> Pydantic model built from __tool_schema__
_SCHEMA_CACHE: dict[str, type[BaseModel]] = {}


def _build_model(tool_name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Dynamically build a Pydantic model from a JSON-schema-like dict."""
    fields: dict[str, Any] = {}
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    TYPE_MAP = {"string": str, "integer": int, "number": float, "boolean": bool, "array": list, "object": dict}
    for field, meta in properties.items():
        py_type = TYPE_MAP.get(meta.get("type", "string"), Any)
        if field in required:
            fields[field] = (py_type, ...)
        else:
            fields[field] = (py_type | None, None)
    return create_model(f"{tool_name}_schema", **fields)


def register_tool_schema(tool_name: str, schema: dict[str, Any]) -> None:
    """Register a JSON schema for a tool so its calls can be validated."""
    _SCHEMA_CACHE[tool_name] = _build_model(tool_name, schema)


def validate_tool_call(tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
    """Validate and coerce parameters against registered schema.

    Returns the validated dict.  Raises ValueError on failure.
    """
    model_cls = _SCHEMA_CACHE.get(tool_name)
    if model_cls is None:
        return parameters  # no schema registered — pass through
    try:
        instance = model_cls(**parameters)
        return instance.model_dump(exclude_none=False)
    except ValidationError as exc:
        raise ValueError(f"Tool '{tool_name}' parameter validation failed: {exc}") from exc
