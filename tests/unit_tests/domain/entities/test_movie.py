"""Tests for Movie entity."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


def test_movie_creation() -> None:
    """Verify that a Movie can be created with all fields populated."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Inception",
        release_date=date(2010, 7, 16),
        directors=("Christopher Nolan",),
        cast=("Leonardo DiCaprio", "Joseph Gordon-Levitt"),
        duration_minutes=148,
        description="A thief who steals corporate secrets...",
    )
    assert movie.title == "Inception"
    assert movie.duration_minutes == 148
    assert movie.description == "A thief who steals corporate secrets..."


def test_movie_rejects_empty_title() -> None:
    """Verify that creating a Movie with an empty title raises ValueError."""
    with pytest.raises(ValueError, match="Movie title cannot be empty"):
        Movie(
            id=MovieId(value="mov-123"),
            title="  ",
            release_date=date(2010, 7, 16),
            directors=("Christopher Nolan",),
            cast=("Actor",),
        )


def test_movie_rejects_no_directors() -> None:
    """Verify that a Movie must have at least one director."""
    with pytest.raises(ValueError, match="Movie must have at least one director"):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            release_date=date(2010, 7, 16),
            directors=(),
            cast=("Actor",),
        )


def test_movie_rejects_empty_director_name() -> None:
    """Verify that a Movie rejects a director with an empty name."""
    with pytest.raises(ValueError, match="Director name cannot be empty"):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            release_date=date(2010, 7, 16),
            directors=("  ",),
            cast=("Actor",),
        )


def test_movie_rejects_non_positive_duration() -> None:
    """Verify that Movie duration must be positive."""
    with pytest.raises(ValueError, match="Movie duration must be positive"):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            release_date=date(2010, 7, 16),
            directors=("Christopher Nolan",),
            cast=("Actor",),
            duration_minutes=0,
        )


def test_movie_allows_none_duration() -> None:
    """Verify that Movie duration can be None (unknown)."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Inception",
        release_date=date(2010, 7, 16),
        directors=("Christopher Nolan",),
        cast=("Actor",),
        duration_minutes=None,
    )
    assert movie.duration_minutes is None


def test_is_recent_returns_true_for_recent_movie() -> None:
    """Verify is_recent returns True for a movie released within the last year."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Recent Movie",
        release_date=date.today() - timedelta(days=30),
        directors=("Director",),
        cast=("Actor",),
    )
    assert movie.is_recent()


def test_is_recent_returns_false_for_old_movie() -> None:
    """Verify is_recent returns False for a movie older than one year."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Old Movie",
        release_date=date.today() - timedelta(days=400),
        directors=("Director",),
        cast=("Actor",),
    )
    assert not movie.is_recent()


def test_is_recent_with_custom_years() -> None:
    """Verify is_recent accepts a custom lookback window."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Barely Recent",
        release_date=date.today() - timedelta(days=365 * 2 + 1),
        directors=("Director",),
        cast=("Actor",),
    )
    assert not movie.is_recent(years=2)


def test_is_recent_returns_false_when_release_date_unknown() -> None:
    """Verify is_recent returns False when release_date is None."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Unknown Release",
        release_date=None,
        directors=("Director",),
        cast=("Actor",),
    )
    assert not movie.is_recent()


def test_movie_accepts_none_directors() -> None:
    """Verify directors can be None when unknown."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="No Director Info",
        release_date=date(2026, 1, 1),
        directors=None,
    )
    assert movie.directors is None


def test_movie_accepts_none_cast() -> None:
    """Verify cast can be None when unknown."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="No Cast Info",
        release_date=date(2026, 1, 1),
        directors=("Director",),
        cast=None,
    )
    assert movie.cast is None


def test_movie_accepts_none_directors_and_cast() -> None:
    """Verify a fully minimal movie with no optional info works."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Minimal",
        release_date=None,
        directors=None,
        cast=None,
    )
    assert movie.title == "Minimal"
    assert movie.release_date is None
    assert movie.directors is None
    assert movie.cast is None
    assert movie.duration_minutes is None
    assert movie.description is None
