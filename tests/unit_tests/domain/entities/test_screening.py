"""Tests for Screening entity."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
    """Provide a sample Cinema for tests."""
    return Cinema(
        id=CinemaId(value="cin-123"),
        name="Test Cinema",
    )


@pytest.fixture
def sample_movie() -> Movie:
    """Provide a sample Movie for tests."""
    return Movie(
        id=MovieId(value="mov-123"),
        title="Test Movie",
    )


@pytest.fixture
def sample_showtime() -> Showtime:
    """Provide a future Showtime for tests."""
    return Showtime(value=datetime.now(timezone.utc) + timedelta(days=1))


def create_screening(
    showtime: Showtime,
    cinema: Cinema,
    movie: Movie,
) -> Screening:
    """Helper to build a Screening with a fixed ID."""
    return Screening(
        id=ScreeningId(value="scr-123"),
        movie=movie,
        cinema=cinema,
        showtime=showtime,
    )


def test_screening_creation(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
) -> None:
    """Verify that a Screening can be created with all fields."""
    screening = create_screening(sample_showtime, sample_cinema, sample_movie)
    assert screening.id == ScreeningId(value="scr-123")
    assert screening.movie == sample_movie
    assert screening.cinema == sample_cinema
    assert screening.showtime == sample_showtime


def test_is_upcoming_returns_true_when_showtime_is_future(
    sample_cinema: Cinema,
    sample_movie: Movie,
) -> None:
    """Verify is_upcoming returns True for a future showtime."""
    future = Showtime(value=datetime.now(timezone.utc) + timedelta(hours=1))
    screening = create_screening(future, sample_cinema, sample_movie)
    assert screening.is_upcoming()


def test_is_upcoming_returns_false_when_showtime_is_past(
    sample_cinema: Cinema,
    sample_movie: Movie,
) -> None:
    """Verify is_upcoming returns False for a past showtime."""
    past = Showtime(value=datetime.now(timezone.utc) - timedelta(hours=1))
    screening = create_screening(past, sample_cinema, sample_movie)
    assert not screening.is_upcoming()


def test_is_upcoming_with_explicit_now(
    sample_cinema: Cinema,
    sample_movie: Movie,
) -> None:
    """Verify is_upcoming respects an explicit ``now`` parameter."""
    showtime = Showtime(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc))
    screening = create_screening(showtime, sample_cinema, sample_movie)
    assert screening.is_upcoming(
        now=datetime(2026, 6, 6, 11, 0, 0, tzinfo=timezone.utc)
    )
    assert not screening.is_upcoming(
        now=datetime(2026, 6, 6, 13, 0, 0, tzinfo=timezone.utc)
    )


def test_has_ended_returns_true_when_showtime_is_past(
    sample_cinema: Cinema,
    sample_movie: Movie,
) -> None:
    """Verify has_ended returns True for a past showtime."""
    past = Showtime(value=datetime.now(timezone.utc) - timedelta(hours=1))
    screening = create_screening(past, sample_cinema, sample_movie)
    assert screening.has_ended()


def test_has_ended_returns_false_when_showtime_is_future(
    sample_cinema: Cinema,
    sample_movie: Movie,
) -> None:
    """Verify has_ended returns False for a future showtime."""
    future = Showtime(value=datetime.now(timezone.utc) + timedelta(hours=1))
    screening = create_screening(future, sample_cinema, sample_movie)
    assert not screening.has_ended()


def test_has_ended_with_explicit_now(
    sample_cinema: Cinema,
    sample_movie: Movie,
) -> None:
    """Verify has_ended respects an explicit ``now`` parameter."""
    showtime = Showtime(value=datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc))
    screening = create_screening(showtime, sample_cinema, sample_movie)
    assert screening.has_ended(now=datetime(2026, 6, 6, 13, 0, 0, tzinfo=timezone.utc))
    assert not screening.has_ended(
        now=datetime(2026, 6, 6, 11, 0, 0, tzinfo=timezone.utc)
    )


def test_screening_str_representation(
    sample_cinema: Cinema,
    sample_movie: Movie,
    sample_showtime: Showtime,
) -> None:
    """Verify the string representation includes movie.id, cinema.id, and showtime."""
    screening = create_screening(sample_showtime, sample_cinema, sample_movie)
    result = str(screening)
    assert str(sample_movie.id) in result
    assert str(sample_cinema.id) in result
    assert str(sample_showtime) in result
