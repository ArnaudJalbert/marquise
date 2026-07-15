"""Shared test fixtures and configuration."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import (
    CinemaId,
    MovieId,
    ScreeningId,
    Showtime,
)


@pytest.fixture
def sample_cinema() -> Cinema:
    """Provide a representative Cinema entity for tests."""
    return Cinema(
        id=CinemaId(value="cin-001"),
        name="Cinéma Test",
        address="123 Test Street",
        city="Montréal",
        website="https://example.com",
    )


@pytest.fixture
def sample_movie() -> Movie:
    """Provide a representative Movie entity for tests."""
    return Movie(
        id=MovieId(value="mov-001"),
        title="The Test Odyssey",
        release_year=2026,
        directors=("Jane Director",),
        duration_minutes=120,
    )


@pytest.fixture
def sample_screening(sample_movie: Movie, sample_cinema: Cinema) -> Screening:
    """Provide a representative Screening entity for tests."""
    return Screening(
        id=ScreeningId(value="scr-001"),
        movie=sample_movie,
        cinema=sample_cinema,
        showtime=Showtime(value=datetime(2026, 6, 27, 19, 30, tzinfo=UTC)),
    )
