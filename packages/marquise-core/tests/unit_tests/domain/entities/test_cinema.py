"""Tests for Cinema entity."""

from __future__ import annotations

import pytest

from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


def test_cinema_creation() -> None:
    """Verify that a Cinema can be created with all optional fields."""
    cinema = Cinema(
        id=CinemaId(value="cin-123"),
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )
    assert cinema.id == CinemaId(value="cin-123")
    assert cinema.name == "Test Cinema"
    assert cinema.address == "123 Test St"
    assert cinema.city == "Montreal"
    assert cinema.website == "https://example.com"


def test_cinema_creation_with_minimal_fields() -> None:
    """Verify that a Cinema can be created with only required fields."""
    cinema = Cinema(id=CinemaId(value="cin-123"), name="Test Cinema")
    assert cinema.name == "Test Cinema"
    assert cinema.address is None
    assert cinema.city is None
    assert cinema.website is None


def test_cinema_rejects_empty_name() -> None:
    """Verify that creating a Cinema with an empty name raises ValueError."""
    with pytest.raises(ValueError, match="Cinema name cannot be empty"):
        Cinema(id=CinemaId(value="cin-123"), name="  ")
