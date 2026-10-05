"""Tests for read-query DI wiring."""

from __future__ import annotations

from unittest.mock import MagicMock

from marquise.application.queries import (
    GetCinemaScreeningsQuery,
    GetMovieScreeningsQuery,
    ListCinemaSourceAssignmentsQuery,
    SearchScreeningsQuery,
)
from marquise.infrastructure.di.queries import (
    build_get_cinema_screenings_query,
    build_get_movie_screenings_query,
    build_list_cinema_source_assignments_query,
    build_search_screenings_query,
)


def test_screening_query_builders_use_supplied_pool_and_schema() -> None:
    """Screening queries receive readers and repositories without database I/O."""
    pool = MagicMock()

    cinema = build_get_cinema_screenings_query(pool, "test_schema")
    movie = build_get_movie_screenings_query(pool, "test_schema")
    search = build_search_screenings_query(pool, "test_schema")

    assert isinstance(cinema, GetCinemaScreeningsQuery)
    assert isinstance(movie, GetMovieScreeningsQuery)
    assert isinstance(search, SearchScreeningsQuery)
    for query in (cinema, movie, search):
        assert query.screening_reader._gateway._pool is pool
        assert query.screening_reader._gateway._schema == "test_schema"
    assert cinema.cinema_repository._gateway._table == '"test_schema".cinemas'
    assert movie.movie_repository._gateway._table == '"test_schema".movies'
    pool.acquire.assert_not_called()


def test_assignment_query_builder_uses_supplied_pool_and_schema() -> None:
    """Assignment query wraps reader without opening database I/O."""
    pool = MagicMock()

    query = build_list_cinema_source_assignments_query(pool, "test_schema")

    assert isinstance(query, ListCinemaSourceAssignmentsQuery)
    assert query._reader._pool is pool
    assert query._reader._schema == "test_schema"
    pool.acquire.assert_not_called()
