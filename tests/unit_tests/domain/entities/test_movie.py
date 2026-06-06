"""Tests for Movie entity."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


def test_movie_creation() -> None:
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
    with pytest.raises(ValueError, match="Movie title cannot be empty"):
        Movie(
            id=MovieId(value="mov-123"),
            title="  ",
            release_date=date(2010, 7, 16),
            directors=("Christopher Nolan",),
            cast=("Actor",),
        )


def test_movie_rejects_no_directors() -> None:
    with pytest.raises(ValueError, match="Movie must have at least one director"):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            release_date=date(2010, 7, 16),
            directors=(),
            cast=("Actor",),
        )


def test_movie_rejects_empty_director_name() -> None:
    with pytest.raises(ValueError, match="Director name cannot be empty"):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            release_date=date(2010, 7, 16),
            directors=("  ",),
            cast=("Actor",),
        )


def test_movie_rejects_non_positive_duration() -> None:
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
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Recent Movie",
        release_date=date.today() - timedelta(days=30),
        directors=("Director",),
        cast=("Actor",),
    )
    assert movie.is_recent()


def test_is_recent_returns_false_for_old_movie() -> None:
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Old Movie",
        release_date=date.today() - timedelta(days=400),
        directors=("Director",),
        cast=("Actor",),
    )
    assert not movie.is_recent()


def test_is_recent_with_custom_years() -> None:
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Barely Recent",
        release_date=date.today() - timedelta(days=365 * 2 + 1),
        directors=("Director",),
        cast=("Actor",),
    )
    assert not movie.is_recent(years=2)
