"""Tests for import use-case DI wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.queries.find_stored_movies import FindStoredMoviesQuery
from marquise.application.sources import (
    SourceRegistry,
)
from marquise.application.use_cases.create_movies import CreateMoviesCommand
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.infrastructure.di.import_use_cases import (
    build_create_movies_use_case,
    build_create_screenings_use_case,
    build_fetch_screenings_use_case,
    build_find_stored_movies_query,
    build_import_screenings_use_case,
)


def test_fetch_builder_wires_pool_schema_and_registry() -> None:
    """Fetch query receives explicit pool, schema, and source registry."""
    pool = MagicMock()
    registry = create_autospec(SourceRegistry, instance=True)

    query = build_fetch_screenings_use_case(pool, "test_schema", registry)

    assert isinstance(query, FetchScreeningsFromSourceQuery)
    assert query.source_registry is registry
    assert query.cinema_repository._gateway._pool is pool
    assert query.cinema_repository._gateway._table == '"test_schema".cinemas'
    assert query.assignment_repository._gateway._pool is pool
    assert query.assignment_repository._gateway._schema == "test_schema"
    pool.acquire.assert_not_called()


def test_movie_builders_wire_supplied_pool_and_schema() -> None:
    """Movie use cases receive repositories built from explicit collaborators."""
    pool = MagicMock()

    command = build_create_movies_use_case(pool, "test_schema")
    query = build_find_stored_movies_query(pool, "test_schema")

    assert isinstance(command, CreateMoviesCommand)
    assert isinstance(query, FindStoredMoviesQuery)
    assert command._movie_repository._gateway._pool is pool
    assert query._movie_repository._gateway._table == '"test_schema".movies'
    pool.acquire.assert_not_called()


def test_import_builder_passes_fetch_without_acquiring_pool() -> None:
    """Building the workflow keeps its fetch query without opening the pool."""
    pool = MagicMock()
    fetch = create_autospec(FetchScreeningsFromSourceQuery, instance=True)

    command = build_import_screenings_use_case(pool, "test_schema", "key", fetch)

    assert command._fetch_screenings is fetch
    pool.acquire.assert_not_called()


def test_screening_builder_wires_supplied_pool_and_schema() -> None:
    """Screening command receives repository built from explicit collaborators."""
    pool = MagicMock()

    command = build_create_screenings_use_case(pool, "test_schema")

    assert isinstance(command, CreateScreeningsCommand)
    assert command.screening_repository._gateway._pool is pool
    assert command.screening_repository._gateway._schema == "test_schema"
    pool.acquire.assert_not_called()
