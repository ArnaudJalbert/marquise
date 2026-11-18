"""Tests for the MarquiseFactory composition root."""

from __future__ import annotations

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
    ("area", "field", "use_case_type"),
    [
        ("cinemas", "create_cinema_use_case", CreateCinemaUseCase),
        ("cinemas", "delete_cinema_use_case", DeleteCinemaUseCase),
        ("cinemas", "update_cinema_use_case", UpdateCinemaUseCase),
        ("cinemas", "list_cinemas_use_case", ListCinemasUseCase),
        ("cinemas", "get_cinema_use_case", GetCinemaUseCase),
        ("cinemas", "get_cinema_movies_use_case", GetCinemaMoviesUseCase),
        ("cinemas", "get_cinema_screenings_query", GetCinemaScreeningsQuery),
        ("movies", "list_movies_use_case", ListMoviesUseCase),
        ("movies", "get_movie_use_case", GetMovieUseCase),
        ("movies", "get_movie_screenings_query", GetMovieScreeningsQuery),
        ("movies", "refresh_movies_use_case", RefreshMoviesUseCase),
        ("movies", "merge_movies_use_case", MergeMoviesUseCase),
        ("screenings", "browse_screening_movies_query", BrowseScreeningMoviesQuery),
        ("screenings", "count_screening_days_query", CountScreeningDaysQuery),
        ("screenings", "search_screenings_query", SearchScreeningsQuery),
        ("screenings", "get_screening_query", GetScreeningQuery),
        ("screenings", "import_screenings_command", ImportScreeningsCommand),
        ("sources", "list_registry_sources_use_case", ListRegistrySourcesUseCase),
        ("sources", "create_source_use_case", CreateSourceUseCase),
        ("sources", "list_sources_use_case", ListSourcesUseCase),
        ("sources", "delete_source_use_case", DeleteSourceUseCase),
        ("sources", "assign_source_use_case", AssignSourceUseCase),
        ("sources", "unassign_source_use_case", UnassignSourceUseCase),
        ("sources", "get_cinema_source_use_case", GetCinemaSourceUseCase),
        (
            "sources",
            "list_cinema_source_assignments_query",
            ListCinemaSourceAssignmentsQuery,
        ),
    ],
)
def test_factory_wires_every_use_case_in_its_area(
    database: MagicMock, area: str, field: str, use_case_type: type
) -> None:
    """Each use case sits in its area under the snake_case name of its class."""
    factory = MarquiseFactory(SETTINGS, database)

    assert isinstance(getattr(getattr(factory, area), field), use_case_type)


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
