"""Tests for read-query DI wiring."""

from __future__ import annotations

from unittest.mock import MagicMock

from marquise.application.queries.get_cinema_screenings import GetCinemaScreeningsQuery
from marquise.application.queries.get_cinema_source import GetCinemaSourceQuery
from marquise.application.queries.get_movie_screenings import GetMovieScreeningsQuery
from marquise.application.queries.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.queries.list_sources import ListSourcesQuery
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.infrastructure.di.queries import (
    build_get_cinema_screenings_query,
    build_get_cinema_source_query,
    build_get_movie_screenings_query,
    build_list_cinema_source_assignments_query,
    build_list_sources_query,
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


def test_assignment_query_builders_use_supplied_pool_and_schema() -> None:
    """Assignment queries wrap the reader gateway without opening database I/O."""
    pool = MagicMock()

    list_all = build_list_cinema_source_assignments_query(pool, "test_schema")
    get_source = build_get_cinema_source_query(pool, "test_schema")

    assert isinstance(list_all, ListCinemaSourceAssignmentsQuery)
    assert isinstance(get_source, GetCinemaSourceQuery)
    for query in (list_all, get_source):
        assert query._reader._gateway._pool is pool
        assert query._reader._gateway._schema == "test_schema"
    pool.acquire.assert_not_called()


def test_list_sources_query_builder_uses_supplied_pool_and_schema() -> None:
    """Source listing reads through its gateway without opening database I/O."""
    pool = MagicMock()

    query = build_list_sources_query(pool, "test_schema")

    assert isinstance(query, ListSourcesQuery)
    gateway = query._source_definition_reader._gateway
    assert gateway._pool is pool
    assert gateway._schema == "test_schema"
    pool.acquire.assert_not_called()
