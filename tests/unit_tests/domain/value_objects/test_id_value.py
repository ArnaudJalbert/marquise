"""Tests for IdValue value object."""

from __future__ import annotations

from marquise.domain.value_objects.id_value import IdValue


def test_id_value_str() -> None:
    idv = IdValue(value="test-id")
    assert str(idv) == "test-id"


def test_id_value_hash() -> None:
    idv1 = IdValue(value="test-id")
    idv2 = IdValue(value="test-id")
    assert hash(idv1) == hash(idv2)


def test_id_value_hash_differs_for_different_values() -> None:
    idv1 = IdValue(value="id-1")
    idv2 = IdValue(value="id-2")
    assert hash(idv1) != hash(idv2)
