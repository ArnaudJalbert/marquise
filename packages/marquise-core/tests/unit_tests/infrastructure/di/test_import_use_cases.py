"""Tests for import use-case DI wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.repositories import SourceRegistryQuery
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.infrastructure.di.import_use_cases import (
    build_create_movies_use_case,
    build_create_screenings_use_case,
    build_fetch_screenings_use_case,
)
from marquise.infrastructure.sources.tmdb import TmdbSearchGateway


def test_fetch_builder_wires_pool_schema_and_registry() -> None:
    """Fetch query receives explicit pool, schema, and source registry."""
    pool = MagicMock()
    registry = create_autospec(SourceRegistryQuery, instance=True)

    query = build_fetch_screenings_use_case(pool, "test_schema", registry)

    assert isinstance(query, FetchScreeningsFromSourceQuery)
    assert query.source_registry is registry
    assert query.cinema_repository._gateway._pool is pool
    assert query.cinema_repository._gateway._table == '"test_schema".cinemas'
    assert query.assignment_repository._gateway._pool is pool
    assert query.assignment_repository._gateway._schema == "test_schema"
    pool.acquire.assert_not_called()


def test_movie_builder_wires_supplied_pool_and_schema() -> None:
    """Movie command receives repository built from explicit collaborators."""
    pool = MagicMock()

    command = build_create_movies_use_case(pool, "test_schema", "fake-key")

    assert isinstance(command, CreateMissingMoviesCommand)
    assert isinstance(command.tmdb_search, TmdbSearchGateway)
    assert command.movie_repository._gateway._pool is pool
    assert command.movie_repository._gateway._table == '"test_schema".movies'
    pool.acquire.assert_not_called()


def test_screening_builder_wires_supplied_pool_and_schema() -> None:
    """Screening command receives repository built from explicit collaborators."""
    pool = MagicMock()

    command = build_create_screenings_use_case(pool, "test_schema")

    assert isinstance(command, CreateScreeningsCommand)
    assert command.screening_repository._gateway._pool is pool
    assert command.screening_repository._gateway._schema == "test_schema"
    pool.acquire.assert_not_called()
