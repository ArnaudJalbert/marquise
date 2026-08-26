"""Tests for Movie entity."""

from __future__ import annotations

from datetime import datetime

import pytest

from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


def test_movie_creation() -> None:
    """Verify that a Movie can be created with all fields populated."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Inception",
        release_year=2010,
        directors=("Christopher Nolan",),
        cast=("Leonardo DiCaprio", "Joseph Gordon-Levitt"),
        duration_minutes=148,
        description="A thief who steals corporate secrets...",
        poster_url="https://example.com/poster.jpg",
        trailer_url="https://example.com/trailer",
        genres=("Sci-Fi", "Action"),
        original_title="Inception",
        rating="PG-13",
        origin_countries=("United States", "United Kingdom"),
    )
    assert movie.title == "Inception"
    assert movie.duration_minutes == 148
    assert movie.description == "A thief who steals corporate secrets..."
    assert movie.poster_url == "https://example.com/poster.jpg"
    assert movie.genres == ("Sci-Fi", "Action")


def test_movie_title_key_ignores_case_articles_and_punctuation() -> None:
    """Verify title variants share one canonical key."""
    assert Movie.title_key("The Odyssey: Part One") == "odyssey part one"


def test_movie_rejects_empty_title() -> None:
    """Verify that creating a Movie with an empty title raises ValueError."""
    with pytest.raises(ValueError, match="Movie title cannot be empty"):
        Movie(
            id=MovieId(value="mov-123"),
            title="  ",
            directors=("Christopher Nolan",),
        )


def test_movie_rejects_no_directors() -> None:
    """Verify that a Movie must have at least one director."""
    with pytest.raises(ValueError, match="Movie must have at least one director"):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            directors=(),
        )


def test_movie_rejects_empty_director_name() -> None:
    """Verify that a Movie rejects a director with an empty name."""
    with pytest.raises(ValueError, match="Director name cannot be empty"):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            directors=("  ",),
        )


def test_movie_rejects_non_positive_duration() -> None:
    """Verify that Movie duration must be positive."""
    with pytest.raises(ValueError, match="Movie duration must be positive"):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            directors=("Christopher Nolan",),
            duration_minutes=0,
        )


def test_movie_rejects_non_positive_release_year() -> None:
    """Verify that Movie release year must be positive."""
    with pytest.raises(ValueError, match="Movie release year must be positive"):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            directors=("Christopher Nolan",),
            release_year=0,
        )


def test_movie_allows_none_duration() -> None:
    """Verify that Movie duration can be None (unknown)."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Inception",
        directors=("Christopher Nolan",),
        duration_minutes=None,
    )
    assert movie.duration_minutes is None


def test_is_recent_returns_true_for_recent_movie() -> None:
    """Verify is_recent returns True for a movie released within the last year."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Recent Movie",
        release_year=datetime.now().year,
        directors=("Director",),
    )
    assert movie.is_recent()


def test_is_recent_returns_false_for_old_movie() -> None:
    """Verify is_recent returns False for a movie older than one year."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Old Movie",
        release_year=datetime.now().year - 5,
        directors=("Director",),
    )
    assert not movie.is_recent()


def test_is_recent_with_custom_years() -> None:
    """Verify is_recent accepts a custom lookback window."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Barely Recent",
        release_year=datetime.now().year - 2,
        directors=("Director",),
    )
    assert movie.is_recent(years=2)

    old_movie = Movie(
        id=MovieId(value="mov-456"),
        title="Not Recent",
        release_year=datetime.now().year - 3,
        directors=("Director",),
    )
    assert not old_movie.is_recent(years=2)


def test_is_recent_returns_false_when_release_year_unknown() -> None:
    """Verify is_recent returns False when release_year is None."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Unknown Release",
        release_year=None,
        directors=("Director",),
    )
    assert not movie.is_recent()


def test_movie_accepts_none_directors() -> None:
    """Verify directors can be None when unknown."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="No Director Info",
        release_year=2026,
        directors=None,
    )
    assert movie.directors is None


def test_movie_accepts_none_cast() -> None:
    """Verify cast can be None when unknown."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="No Cast Info",
        release_year=2026,
        directors=("Director",),
        cast=None,
    )
    assert movie.cast is None


def test_movie_accepts_none_optional_fields() -> None:
    """Verify a fully minimal movie with no optional info works."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Minimal",
    )
    assert movie.title == "Minimal"
    assert movie.release_year is None
    assert movie.directors is None
    assert movie.cast is None
    assert movie.duration_minutes is None
    assert movie.description is None
    assert movie.poster_url is None
    assert movie.trailer_url is None
    assert movie.genres is None
    assert movie.original_title is None
    assert movie.rating is None
    assert movie.origin_countries is None
