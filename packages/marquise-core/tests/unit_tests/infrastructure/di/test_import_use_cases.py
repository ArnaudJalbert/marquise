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
from marquise.application.use_cases.enrich_movies import EnrichMoviesUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.match_movies import MatchMoviesUseCase
from marquise.application.use_cases.resolve_movies import ResolveMoviesCommand
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


def test_import_builder_wires_every_step() -> None:
    """The coordinator receives each use case it sequences."""
    pool = MagicMock()
    fetch = create_autospec(FetchScreeningsFromSourceQuery, instance=True)

    command = build_import_screenings_use_case(pool, "test_schema", "key", fetch)

    assert isinstance(command, ImportScreeningsCommand)
    assert command._fetch_screenings is fetch
    resolve_movies = command._resolve_movies
    assert isinstance(resolve_movies, ResolveMoviesCommand)
    assert isinstance(resolve_movies._match_movies, MatchMoviesUseCase)
    assert isinstance(resolve_movies._find_stored_movies, FindStoredMoviesQuery)
    assert isinstance(resolve_movies._create_movies, CreateMoviesCommand)
    assert isinstance(command._create_screenings, CreateScreeningsCommand)
    assert isinstance(command._enrich_movies, EnrichMoviesUseCase)
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
