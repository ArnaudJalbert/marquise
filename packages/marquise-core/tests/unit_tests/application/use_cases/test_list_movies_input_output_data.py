"""Tests for ListMoviesUseCase InputData, MovieData, and OutputData validation."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.list_movies import ListMoviesUseCase


def test_input_data_rejects_empty_title() -> None:
    """Verify InputData rejects an empty title string."""
    with pytest.raises(ValueError, match="title must not be empty when provided"):
        ListMoviesUseCase.InputData(title="")


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


def test_output_data_rejects_negative_total() -> None:
    """Verify OutputData rejects a negative total."""
    with pytest.raises(ValueError, match="total must not be negative"):
        ListMoviesUseCase.OutputData(movies=[], total=-1)
