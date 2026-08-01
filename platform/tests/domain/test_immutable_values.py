"""Tests for deep domain immutability and canonical JSON conversion."""

import json

import pytest

from editorial_tres.domain.immutable_values import (
    canonical_json,
    deep_freeze,
    deep_to_jsonable,
)


def test_deep_freeze_detaches_and_immutabilizes_nested_values() -> None:
    source = {
        "editorial": {
            "labels": ["opening", "reviewed"],
            "settings": {"visible": True},
        }
    }

    frozen = deep_freeze(source)
    source["editorial"]["labels"].append("mutated")
    source["editorial"]["settings"]["visible"] = False

    assert frozen["editorial"]["labels"] == ("opening", "reviewed")
    assert frozen["editorial"]["settings"]["visible"] is True
    with pytest.raises(TypeError):
        frozen["editorial"]["settings"]["visible"] = False
    with pytest.raises(AttributeError):
        frozen["editorial"]["labels"].append("forbidden")


def test_deep_to_jsonable_converts_nested_immutable_values_recursively() -> None:
    frozen = deep_freeze(
        {
            "editorial": {
                "labels": ["opening", "reviewed"],
                "settings": {"visible": True},
            },
            "tags": {"zeta", "alpha"},
        }
    )

    converted = deep_to_jsonable(frozen)

    assert converted == {
        "editorial": {
            "labels": ["opening", "reviewed"],
            "settings": {"visible": True},
        },
        "tags": ["alpha", "zeta"],
    }
    assert json.loads(json.dumps(converted)) == converted


def test_canonical_json_is_stable_for_equivalent_unordered_values() -> None:
    first = {"tags": frozenset({"zeta", "alpha"}), "value": 1}
    second = {"value": 1, "tags": frozenset({"alpha", "zeta"})}

    assert canonical_json(first) == canonical_json(second)
