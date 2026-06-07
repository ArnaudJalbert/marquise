"""Tests for CinemaSourceAssignment entity."""

from __future__ import annotations

import pytest

from marquise.domain.entities import CinemaSourceAssignment
from marquise.domain.value_objects import CinemaId, SourceName


def test_cinema_source_assignment_creation() -> None:
    """Verify CinemaSourceAssignment can be created with valid data."""
    assignment = CinemaSourceAssignment(
        cinema_id=CinemaId(value="cin-001"),
        source_name=SourceName(value="cineplex"),
    )
    assert assignment.cinema_id == CinemaId(value="cin-001")
    assert assignment.source_name == SourceName(value="cineplex")


def test_cinema_source_assignment_rejects_empty_cinema_id() -> None:
    """Verify creating with empty cinema_id raises ValueError."""
    with pytest.raises(ValueError, match="value must not be empty or whitespace-only"):
        CinemaSourceAssignment(
            cinema_id=CinemaId(value="  "),
            source_name=SourceName(value="cineplex"),
        )


def test_cinema_source_assignment_rejects_empty_source_name() -> None:
    """Verify creating with empty source_name raises ValueError."""
    with pytest.raises(ValueError, match="value must not be empty or whitespace-only"):
        CinemaSourceAssignment(
            cinema_id=CinemaId(value="cin-001"),
            source_name=SourceName(value="  "),
        )
