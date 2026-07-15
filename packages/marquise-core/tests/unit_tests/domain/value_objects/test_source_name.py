"""Tests for SourceName value object."""

from __future__ import annotations

from marquise.domain.value_objects.source_name import SourceName


def test_source_name_creation() -> None:
    """Verify SourceName wraps a string value via IdValue."""
    name = SourceName(value="cineplex")
    assert name.value == "cineplex"


def test_source_name_str() -> None:
    """Verify SourceName string representation matches the wrapped value."""
    name = SourceName(value="cineplex")
    assert str(name) == "cineplex"


def test_source_name_hash() -> None:
    """Verify SourceName hashing is based on value equality."""
    name1 = SourceName(value="cineplex")
    name2 = SourceName(value="cineplex")
    assert hash(name1) == hash(name2)


def test_source_name_hash_differs() -> None:
    """Verify that different values produce different hashes."""
    name1 = SourceName(value="cineplex")
    name2 = SourceName(value="cinema_du_parc")
    assert hash(name1) != hash(name2)
