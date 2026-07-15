"""Smoke tests for the shared conftest fixtures."""

from __future__ import annotations

from marquise.domain.entities import Cinema, Movie, Screening


def test_sample_cinema_fixture(sample_cinema: Cinema) -> None:
    """The shared sample_cinema fixture yields a valid Cinema."""
    assert sample_cinema.name == "Cinéma Test"
    assert sample_cinema.city == "Montréal"


def test_sample_movie_fixture(sample_movie: Movie) -> None:
    """The shared sample_movie fixture yields a valid Movie."""
    assert sample_movie.title == "The Test Odyssey"
    assert sample_movie.release_year == 2026


def test_sample_screening_fixture(sample_screening: Screening) -> None:
    """The shared sample_screening fixture links the movie and cinema."""
    assert sample_screening.movie.id.value == "mov-001"
    assert sample_screening.cinema.id.value == "cin-001"
    assert sample_screening.showtime.value.tzinfo is not None
