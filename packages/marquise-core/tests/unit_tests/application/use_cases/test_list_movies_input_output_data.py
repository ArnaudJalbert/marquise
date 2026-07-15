"""Tests for ListMoviesUseCase InputData, MovieData, and OutputData validation."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.list_movies import ListMoviesUseCase


def test_input_data_defaults_to_none_title() -> None:
    """Verify InputData defaults title to None."""
    data = ListMoviesUseCase.InputData()
    assert data.title is None


def test_input_data_allows_valid_title() -> None:
    """Verify InputData accepts a valid title."""
    data = ListMoviesUseCase.InputData(title="Movie")
    assert data.title == "Movie"


def test_input_data_rejects_empty_title() -> None:
    """Verify InputData rejects an empty title string."""
    with pytest.raises(ValueError, match="title must not be empty when provided"):
        ListMoviesUseCase.InputData(title="")


def test_input_data_rejects_whitespace_title() -> None:
    """Verify InputData rejects a whitespace-only title."""
    with pytest.raises(ValueError, match="title must not be empty when provided"):
        ListMoviesUseCase.InputData(title="   ")


def test_input_data_rejects_page_below_one() -> None:
    """Verify InputData rejects a page less than 1."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        ListMoviesUseCase.InputData(page=0)


def test_input_data_rejects_non_positive_size() -> None:
    """Verify InputData rejects a size less than 1 when provided."""
    with pytest.raises(ValueError, match="size must be positive when provided"):
        ListMoviesUseCase.InputData(size=0)


def test_input_data_allows_none_size() -> None:
    """Verify InputData allows size=None (unbounded)."""
    data = ListMoviesUseCase.InputData(size=None)
    assert data.size is None


def test_movie_data_creation() -> None:
    """Verify MovieData can be created with all fields."""
    data = ListMoviesUseCase.MovieData(
        id="id-1",
        title="Test Movie",
        release_year=2024,
        directors=("Director A",),
        cast=("Actor A",),
        duration_minutes=100,
        description="A test movie.",
        poster_url="https://example.com/poster.jpg",
        trailer_url="https://example.com/trailer.mp4",
        genres=("Drama",),
        original_title="Le Film Test",
        rating="13+",
        origin_countries=("Canada",),
    )
    assert data.id == "id-1"
    assert data.title == "Test Movie"
    assert data.release_year == 2024
    assert data.directors == ("Director A",)
    assert data.cast == ("Actor A",)
    assert data.duration_minutes == 100
    assert data.description == "A test movie."
    assert data.poster_url == "https://example.com/poster.jpg"
    assert data.trailer_url == "https://example.com/trailer.mp4"
    assert data.genres == ("Drama",)
    assert data.original_title == "Le Film Test"
    assert data.rating == "13+"
    assert data.origin_countries == ("Canada",)


def test_movie_data_allows_none_optional_fields() -> None:
    """Verify MovieData allows None for all optional fields."""
    data = ListMoviesUseCase.MovieData(id="id-1", title="Test Movie")
    assert data.release_year is None
    assert data.directors is None
    assert data.cast is None
    assert data.duration_minutes is None
    assert data.description is None
    assert data.poster_url is None
    assert data.trailer_url is None
    assert data.genres is None
    assert data.original_title is None
    assert data.rating is None
    assert data.origin_countries is None


def test_movie_data_rejects_empty_id() -> None:
    """Verify MovieData rejects an empty id."""
    with pytest.raises(ValueError, match="id must not be empty"):
        ListMoviesUseCase.MovieData(id="", title="Test Movie")


def test_movie_data_rejects_whitespace_id() -> None:
    """Verify MovieData rejects a whitespace-only id."""
    with pytest.raises(ValueError, match="id must not be empty"):
        ListMoviesUseCase.MovieData(id="   ", title="Test Movie")


def test_movie_data_rejects_empty_title() -> None:
    """Verify MovieData rejects an empty title."""
    with pytest.raises(ValueError, match="title must not be empty"):
        ListMoviesUseCase.MovieData(id="id-1", title="")


def test_movie_data_rejects_whitespace_title() -> None:
    """Verify MovieData rejects a whitespace-only title."""
    with pytest.raises(ValueError, match="title must not be empty"):
        ListMoviesUseCase.MovieData(id="id-1", title="   ")


def test_output_data_creation() -> None:
    """Verify OutputData can be created with a list of MovieData."""
    movie = ListMoviesUseCase.MovieData(id="id-1", title="Test Movie")
    data = ListMoviesUseCase.OutputData(movies=[movie], total=1)
    assert len(data.movies) == 1
    assert data.movies[0].id == "id-1"
    assert data.movies[0].title == "Test Movie"
    assert data.total == 1


def test_output_data_empty_list() -> None:
    """Verify OutputData accepts an empty list."""
    data = ListMoviesUseCase.OutputData(movies=[], total=0)
    assert len(data.movies) == 0


def test_output_data_rejects_negative_total() -> None:
    """Verify OutputData rejects a negative total."""
    with pytest.raises(ValueError, match="total must not be negative"):
        ListMoviesUseCase.OutputData(movies=[], total=-1)
