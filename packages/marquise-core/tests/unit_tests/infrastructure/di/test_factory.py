"""Tests for the MarquiseFactory composition root."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, create_autospec, patch

import asyncpg
import pytest

from marquise.application.queries.browse_screening_movies import (
    BrowseScreeningMoviesQuery,
)
from marquise.application.queries.count_screening_days import CountScreeningDaysQuery
from marquise.application.queries.get_cinema_screenings import (
    GetCinemaScreeningsQuery,
)
from marquise.application.queries.get_movie_screenings import (
    GetMovieScreeningsQuery,
)
from marquise.application.queries.get_screening import GetScreeningQuery
from marquise.application.queries.list_cinema_source_assignments import (
    ListCinemaSourceAssignmentsQuery,
)
from marquise.application.queries.search_screenings import SearchScreeningsQuery
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.merge_movies import MergeMoviesUseCase
from marquise.application.use_cases.refresh_movies import RefreshMoviesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.infrastructure.di.factory import MarquiseFactory
from marquise.infrastructure.supabase.config.settings import Settings
from marquise.infrastructure.supabase.database import Database
from marquise.interface_adapters.repositories.source_registry import SourceRegistry

SETTINGS = Settings(
    database_url="postgresql://u:p@localhost:5432/db",
    cineplex_api_key="cineplex-key",
    tmdb_api_key="tmdb-key",
    schema="marquise",
)


@pytest.fixture
def database() -> MagicMock:
    """Provide a connected database whose pool is never used."""
    connected = create_autospec(Database, instance=True)
    connected.pool = create_autospec(asyncpg.Pool, instance=True)
    return connected


@pytest.mark.parametrize(
    ("path", "use_case_type"),
    [
        ("cinemas.create_cinema_use_case", CreateCinemaUseCase),
        ("cinemas.delete_cinema_use_case", DeleteCinemaUseCase),
        ("cinemas.update_cinema_use_case", UpdateCinemaUseCase),
        ("cinemas.list_cinemas_use_case", ListCinemasUseCase),
        ("cinemas.get_cinema_use_case", GetCinemaUseCase),
        ("cinemas.get_cinema_movies_use_case", GetCinemaMoviesUseCase),
        ("cinemas.get_cinema_screenings_query", GetCinemaScreeningsQuery),
        ("movies.list_movies_use_case", ListMoviesUseCase),
        ("movies.get_movie_use_case", GetMovieUseCase),
        ("movies.get_movie_screenings_query", GetMovieScreeningsQuery),
        ("movies.refresh_movies_use_case", RefreshMoviesUseCase),
        ("movies.merge_movies_use_case", MergeMoviesUseCase),
        ("screenings.browse_screening_movies_query", BrowseScreeningMoviesQuery),
        ("screenings.count_screening_days_query", CountScreeningDaysQuery),
        ("screenings.search_screenings_query", SearchScreeningsQuery),
        ("screenings.get_screening_query", GetScreeningQuery),
        ("screenings.import_screenings_command", ImportScreeningsCommand),
        ("sources.list_registry_sources_use_case", ListRegistrySourcesUseCase),
        ("sources.create_source_use_case", CreateSourceUseCase),
        ("sources.list_sources_use_case", ListSourcesUseCase),
        ("sources.delete_source_use_case", DeleteSourceUseCase),
        ("sources.assign_source_use_case", AssignSourceUseCase),
        ("sources.unassign_source_use_case", UnassignSourceUseCase),
        ("sources.get_cinema_source_use_case", GetCinemaSourceUseCase),
        (
            "sources.list_cinema_source_assignments_query",
            ListCinemaSourceAssignmentsQuery,
        ),
    ],
)
def test_factory_wires_every_use_case_in_its_area(
    database: MagicMock, path: str, use_case_type: type
) -> None:
    """Each use case sits in its area under the snake_case name of its class."""
    factory = MarquiseFactory(SETTINGS, database)

    assert isinstance(_use_case_at(factory, path), use_case_type)


@dataclass(frozen=True, slots=True)
class SchemaCase:
    """A use case to run through the factory and the table its SQL must name."""

    path: str
    table: str
    input_fields: dict[str, str | datetime] = field(default_factory=dict)


@pytest.fixture
def connection(database: MagicMock) -> MagicMock:
    """Provide the pool's connection, answering with one cinema and no rows."""
    acquired = create_autospec(asyncpg.Connection, instance=True)
    acquired.fetch.return_value = []
    acquired.fetchval.return_value = 1
    acquired.fetchrow.return_value = {
        "id": "cin-1",
        "name": "Cinema One",
        "address": None,
        "city": None,
        "website": None,
    }

    @asynccontextmanager
    async def acquire() -> AsyncIterator[MagicMock]:
        yield acquired

    database.pool.acquire.side_effect = acquire
    return acquired


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        SchemaCase("cinemas.list_cinemas_use_case", "cinemas"),
        SchemaCase(
            "cinemas.get_cinema_movies_use_case",
            "screenings",
            {
                "cinema_id": "cin-1",
                "start_date": datetime(2026, 11, 18, tzinfo=UTC),
                "end_date": datetime(2026, 11, 19, tzinfo=UTC),
            },
        ),
        SchemaCase("movies.list_movies_use_case", "movies"),
        SchemaCase("screenings.search_screenings_query", "screenings"),
        SchemaCase("sources.list_sources_use_case", "source_definitions"),
        SchemaCase(
            "sources.list_cinema_source_assignments_query",
            "cinema_source_assignments",
        ),
    ],
    ids=lambda case: case.path,
)
async def test_use_cases_query_the_open_pool_in_the_configured_schema(
    database: MagicMock, connection: MagicMock, case: SchemaCase
) -> None:
    """A use case run through the factory sends its SQL to the configured schema."""
    settings = Settings(database_url=SETTINGS.database_url, schema="custom_schema")
    use_case = _use_case_at(MarquiseFactory(settings, database), case.path)

    await use_case.execute(use_case.InputData(**case.input_fields))

    assert f'"custom_schema".{case.table}' in _executed_sql(connection)


# Any: each path names a different use case type, and callers use its InputData.
def _use_case_at(factory: MarquiseFactory, path: str) -> Any:  # noqa: ANN401
    """Return the use case at an "area.field" path on the factory."""
    area, use_case_field = path.split(".")
    return getattr(getattr(factory, area), use_case_field)


def _executed_sql(connection: MagicMock) -> str:
    """Join the SQL of every read the connection served."""
    calls = [
        *connection.fetch.call_args_list,
        *connection.fetchrow.call_args_list,
        *connection.fetchval.call_args_list,
    ]
    return " ".join(call.args[0] for call in calls)


def test_factory_wires_without_touching_the_pool(database: MagicMock) -> None:
    """Wiring builds objects only and sends no query to the database."""
    MarquiseFactory(SETTINGS, database)

    database.pool.acquire.assert_not_called()
    database.ping.assert_not_awaited()


def test_factory_builds_the_source_registry_once(database: MagicMock) -> None:
    """Import and registry listing share one registry built with the Cineplex key."""
    with patch(
        "marquise.infrastructure.di.factory.build_source_registry",
        return_value=SourceRegistry(),
    ) as build_source_registry:
        MarquiseFactory(SETTINGS, database)

    build_source_registry.assert_called_once_with("cineplex-key")


@pytest.mark.asyncio
@pytest.mark.parametrize("healthy", [True, False])
async def test_check_database_health_reports_the_database_ping(
    database: MagicMock, healthy: bool
) -> None:
    """The health check reports whatever the database ping returns."""
    database.ping.return_value = healthy
    factory = MarquiseFactory(SETTINGS, database)

    assert await factory.check_database_health() is healthy
    database.ping.assert_awaited_once()
