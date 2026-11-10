"""Tests for Movie entity."""

from __future__ import annotations

from typing import cast

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


@pytest.mark.parametrize(
    ("title", "film"),
    [
        ("Carrie (VOSTF)", "Carrie"),
        ("Carrie (VF)", "Carrie"),
        ("In Bruges (VOA)", "In Bruges"),
        ("Gentle Monster (VOSTA)", "Gentle Monster"),
        ("Le déclin de l’empire américain(VOF)", "Le déclin de l’empire américain"),
        ("Fjord (Multilingual w/e.s.t.)", "Fjord"),
        ("Fjord (multilingue s.t.f.)", "Fjord"),
        ("Godzilla Minus Zero (Japonaise avec s.t.f.)", "Godzilla Minus Zero"),
        ("THE SHINING (anglais avec s.t.f.)", "THE SHINING"),
        ("Rembrandt (Français s.t.f.)", "Rembrandt"),
        ("Street Fighter : le film (version française)", "Street Fighter : le film"),
        ("Ramayana (Hindi w/e.s.t.) - An IMAX 3D Experience", "Ramayana"),
        ("RAMAYANA HIN.ENG.SUB", "RAMAYANA"),
        ("Ramayana (English Dubbed)", "Ramayana"),
        ("Rammstein - Live in Mexico City (German)", "Rammstein - Live in Mexico City"),
        ("Scream: 30e anniversaire", "Scream"),
        ("Jacquot de Nantes [DERNIÈRE SÉANCE]", "Jacquot de Nantes"),
        ("L&apos;aile ou la cuisse (VOF)", "L'aile ou la cuisse"),
        ("Johnny English", "Johnny English"),
        ("The English Patient", "The English Patient"),
    ],
)
def test_search_title_strips_only_trailing_screening_labels(
    title: str, film: str
) -> None:
    """Cinema version labels are removed; titles ending in a language are kept."""
    assert Movie.search_title(title) == film


def test_title_key_ignores_case_accents_and_labels() -> None:
    """Label and case variants of one film share a key."""
    assert (
        Movie.title_key("GODZILLA MINUS ZERO")
        == Movie.title_key("Godzilla Minus Zero (Japanese w/e.s.t.)")
        == "godzilla minus zero"
    )
    assert Movie.title_key("SPIDER MAN BRAND NEW DAY") == Movie.title_key(
        "Spider-Man: Brand New Day"
    )
    assert Movie.title_key("Amélie") == Movie.title_key("AMELIE")
    assert Movie.title_key("SHAUN THE SHEEP: BEAST OF MOSSY BOTTOM") == (
        Movie.title_key("Shaun the Sheep: The Beast of Mossy Bottom")
    )
    assert Movie.title_key("The A") == "the a"


@pytest.mark.parametrize(
    ("left", "right", "overlap"),
    [
        ("Street Fighter : le film (version française)", "Street Fighter", True),
        ("Ramayana (Hindi w/e.s.t.)", "Ramayana: Rise of a Legend", True),
        ("SUSPIRIA", "Suspiria", True),
        ("Shock", "Aftershock", False),
        ("Elf", "Elf 2", False),
        ("Heated Rivalry - Episodes 1 & 2", "Heated Rivalry - Episodes 3 & 4", False),
    ],
)
def test_titles_overlap_by_whole_words(left: str, right: str, overlap: bool) -> None:
    """Containment needs whole words and enough title to be distinctive."""
    assert Movie.titles_overlap(left, right) is overlap


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


@pytest.mark.parametrize("tmdb_rating", [-0.1, 10.1, float("nan"), float("inf"), True])
def test_movie_rejects_invalid_tmdb_rating(tmdb_rating: float | bool) -> None:
    """TMDB scores must be finite numbers from zero through ten."""
    with pytest.raises(ValueError, match="Movie TMDB rating must be between 0 and 10"):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            tmdb_rating=tmdb_rating,
        )


@pytest.mark.parametrize("tmdb_vote_count", [-1, 1.5, True])
def test_movie_rejects_invalid_tmdb_vote_count(
    tmdb_vote_count: int | float | bool,
) -> None:
    """TMDB vote counts must be non-negative integers."""
    with pytest.raises(
        ValueError, match="Movie TMDB vote count must be a non-negative integer"
    ):
        Movie(
            id=MovieId(value="mov-123"),
            title="Inception",
            tmdb_vote_count=cast(int, tmdb_vote_count),
        )


def test_movie_accepts_zero_tmdb_score_and_vote_count() -> None:
    """Zero is a valid score and vote count from TMDB."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Inception",
        tmdb_rating=0.0,
        tmdb_vote_count=0,
    )
    assert movie.tmdb_rating == 0.0
    assert movie.tmdb_vote_count == 0


def test_movie_allows_none_duration() -> None:
    """Verify that Movie duration can be None (unknown)."""
    movie = Movie(
        id=MovieId(value="mov-123"),
        title="Inception",
        directors=("Christopher Nolan",),
        duration_minutes=None,
    )
    assert movie.duration_minutes is None


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
