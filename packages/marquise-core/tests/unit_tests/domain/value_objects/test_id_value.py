"""Tests for IdValue value object."""

import pytest

from marquise.domain.value_objects.id_value import IdValue


def test_id_value_str() -> None:
    """Verify IdValue string representation matches the wrapped value."""
    idv = IdValue(value="test-id")
    assert str(idv) == "test-id"


def test_id_value_hash() -> None:
    """Verify IdValue hashing is based on value equality."""
    idv1 = IdValue(value="test-id")
    idv2 = IdValue(value="test-id")
    assert hash(idv1) == hash(idv2)


def test_id_value_hash_differs_for_different_values() -> None:
    """Verify that different values produce different hashes."""
    idv1 = IdValue(value="id-1")
    idv2 = IdValue(value="id-2")
    assert hash(idv1) != hash(idv2)


def test_id_value_rejects_empty_string() -> None:
    """Verify IdValue rejects an empty string value."""
    with pytest.raises(ValueError, match="value must not be empty or whitespace-only"):
        IdValue(value="")


def test_id_value_rejects_whitespace_only_string() -> None:
    """Verify IdValue rejects a whitespace-only string value."""
    with pytest.raises(ValueError, match="value must not be empty or whitespace-only"):
        IdValue(value="   ")
