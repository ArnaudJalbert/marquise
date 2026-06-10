"""Tests for CinemaSourceAssignment entity."""

from __future__ import annotations

from marquise.domain.entities import Cinema, CinemaSourceAssignment, SourceDefinition
from marquise.domain.value_objects import CinemaId, SourceName


def test_cinema_source_assignment_creation() -> None:
    """Verify CinemaSourceAssignment can be created with valid data."""
    cinema = Cinema(id=CinemaId(value="cin-001"), name="Test Cinema")
    source = SourceDefinition(
        name=SourceName(value="cineplex"), display_name="Cineplex"
    )
    assignment = CinemaSourceAssignment(cinema=cinema, source=source)
    assert assignment.cinema == cinema
    assert assignment.source == source
