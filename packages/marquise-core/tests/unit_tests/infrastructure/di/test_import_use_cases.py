"""Tests for import use-case DI wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.queries.find_stored_movies import FindStoredMoviesQuery
from marquise.application.repositories import SourceRegistryQuery
from marquise.application.use_cases.create_movies import CreateMoviesCommand
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.infrastructure.di.import_use_cases import (
    build_create_movies_use_case,
    build_create_screenings_use_case,
    build_fetch_screenings_use_case,
    build_find_stored_movies_query,
)


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


def test_screening_builder_wires_supplied_pool_and_schema() -> None:
    """Screening command receives repository built from explicit collaborators."""
    pool = MagicMock()

    command = build_create_screenings_use_case(pool, "test_schema")

    assert isinstance(command, CreateScreeningsCommand)
    assert command.screening_repository._gateway._pool is pool
    assert command.screening_repository._gateway._schema == "test_schema"
    pool.acquire.assert_not_called()


def test_metadata_workflows_are_available_through_factory() -> None:
    """Factory exposes the configured refresh and guarded merge workflows."""
    from marquise import MarquiseFactory
    from marquise.application.use_cases.merge_movies import MergeMoviesUseCase
    from marquise.application.use_cases.refresh_movies import RefreshMoviesUseCase

    factory = MarquiseFactory()
    factory._container._pool = MagicMock()
    assert isinstance(factory.refresh_movies_use_case, RefreshMoviesUseCase)
    assert isinstance(factory.merge_movies_use_case, MergeMoviesUseCase)
