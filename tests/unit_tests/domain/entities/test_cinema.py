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
    )
    assert cinema.id == CinemaId(value="cin-123")
    assert cinema.name == "Test Cinema"
    assert cinema.address == "123 Test St"
    assert cinema.city == "Montreal"


def test_cinema_creation_with_minimal_fields() -> None:
    """Verify that a Cinema can be created with only required fields."""
    cinema = Cinema(id=CinemaId(value="cin-123"), name="Test Cinema")
    assert cinema.name == "Test Cinema"
    assert cinema.address is None
    assert cinema.city is None


def test_cinema_rejects_empty_name() -> None:
    """Verify that creating a Cinema with an empty name raises ValueError."""
    with pytest.raises(ValueError, match="Cinema name cannot be empty"):
        Cinema(id=CinemaId(value="cin-123"), name="  ")


def test_is_located_in_matches_case_insensitive() -> None:
    """Verify is_located_in performs case-insensitive matching."""
    cinema = Cinema(
        id=CinemaId(value="cin-123"),
        name="Test Cinema",
        city="Montreal",
    )
    assert cinema.is_located_in("montreal")
    assert cinema.is_located_in("MONTREAL")
    assert cinema.is_located_in("Montreal")


def test_is_located_in_returns_false_when_no_city() -> None:
    """Verify is_located_in returns False when city is not set."""
    cinema = Cinema(id=CinemaId(value="cin-123"), name="Test Cinema")
    assert not cinema.is_located_in("Montreal")


def test_is_located_in_returns_false_for_different_city() -> None:
    """Verify is_located_in returns False for a non-matching city."""
    cinema = Cinema(
        id=CinemaId(value="cin-123"),
        name="Test Cinema",
        city="Montreal",
    )
    assert not cinema.is_located_in("Quebec")
