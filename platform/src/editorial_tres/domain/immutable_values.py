"""Deep immutability and canonical JSON boundaries for domain values."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date, datetime
from enum import Enum
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel


def deep_freeze(value: Any) -> Any:
    """Recursively freeze JSON-like domain values without changing scalars."""

    if isinstance(value, Mapping):
        return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(deep_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(deep_freeze(item) for item in value)
    return value


def deep_to_jsonable(value: Any) -> Any:
    """Recursively convert immutable domain values at a JSON/SQLite boundary."""

    if isinstance(value, BaseModel):
        return {
            field_name: deep_to_jsonable(getattr(value, field_name))
            for field_name in type(value).model_fields
        }
    if isinstance(value, Mapping):
        converted = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("Las claves de una estructura JSON deben ser strings.")
            converted[key] = deep_to_jsonable(item)
        return converted
    if isinstance(value, (list, tuple)):
        return [deep_to_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        converted = [deep_to_jsonable(item) for item in value]
        return sorted(converted, key=canonical_json)
    if isinstance(value, Enum):
        return deep_to_jsonable(value.value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def canonical_json(value: Any) -> str:
    """Return a deterministic, whitespace-free JSON representation."""

    return json.dumps(
        deep_to_jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
