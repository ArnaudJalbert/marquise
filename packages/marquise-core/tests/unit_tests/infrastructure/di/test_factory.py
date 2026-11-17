"""Tests for the MarquiseFactory composition root."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import AsyncMock, patch

import pytest

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
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.infrastructure.di.factory import MarquiseFactory


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables before each test."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")


@pytest.mark.asyncio
async def test_database_initialization_still_requires_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deferring database configuration does not hide initialization errors."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with patch("marquise.infrastructure.di.factory.load_dotenv"):
        factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        await factory.initialize()


@pytest.mark.asyncio
async def test_initialize_and_shutdown() -> None:
    """Verify initialize opens the pool and shutdown closes it."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        mock_database.connect.assert_awaited_once()
        assert factory._pool is mock_database.pool

        await factory.shutdown()
        mock_database.disconnect.assert_awaited_once()
        assert factory._database is None
        assert factory._pool is None


@pytest.mark.asyncio
async def test_get_screening_query_after_initialize() -> None:
    """Verify get_screening_query returns a GetScreeningQuery."""
    from marquise.application.queries.get_screening import GetScreeningQuery

    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()
        query = factory.get_screening_query
        assert isinstance(query, GetScreeningQuery)
        assert query.screening_reader._gateway._pool is mock_database.pool
        assert query.screening_reader._gateway._schema == "marquise"
        await factory.shutdown()


def test_importing_marquise_does_not_load_dotenv() -> None:
    """Importing the facade reads no .env file."""
    script = (
        "import dotenv\n"
        "calls = []\n"
        "dotenv.load_dotenv = lambda *args, **kwargs: calls.append(args)\n"
        "import marquise\n"
        "assert not calls, 'load_dotenv ran on import'\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.asyncio
async def test_factory_reads_dotenv_before_building_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A database URL found only in .env still reaches the database."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    dotenv_url = "postgresql://dotenv@localhost:5432/db"

    def fake_load_dotenv() -> bool:
        monkeypatch.setenv("DATABASE_URL", dotenv_url)
        return True

    mock_database = AsyncMock()
    with (
        patch(
            "marquise.infrastructure.di.factory.load_dotenv",
            side_effect=fake_load_dotenv,
        ),
        patch(
            "marquise.infrastructure.di.factory.Database", return_value=mock_database
        ) as database,
    ):
        factory = MarquiseFactory()
        await factory.initialize()

    assert database.call_args.args[0].database_url == dotenv_url


def test_list_registry_sources_use_case_needs_no_database() -> None:
    """Listing registry sources works before the pool is opened."""
    factory = MarquiseFactory()

    assert isinstance(
        factory.list_registry_sources_use_case, ListRegistrySourcesUseCase
    )


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_safe_when_not_initialized() -> None:
    """Verify shutdown does not raise when initialize was never called."""
    factory = MarquiseFactory()
    await factory.shutdown()


@pytest.mark.asyncio
async def test_initialize_is_idempotent() -> None:
    """Verify calling initialize twice only creates one pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()
        await factory.initialize()

        mock_database.connect.assert_awaited_once()

        await factory.shutdown()


# ------------------------------------------------------------------
# Configured use-case properties
# ------------------------------------------------------------------


def test_create_cinema_use_case_requires_initialize() -> None:
    """Verify create use case retains factory's pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = factory.create_cinema_use_case


@pytest.mark.asyncio
async def test_create_cinema_use_case_returns_configured_use_case() -> None:
    """Verify factory returns create use case wired to initialized pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        use_case = factory.create_cinema_use_case
        assert isinstance(use_case, CreateCinemaUseCase)
        assert use_case.cinema_repository._gateway._pool is mock_database.pool

        await factory.shutdown()


def test_delete_cinema_use_case_requires_initialize() -> None:
    """Verify delete use case retains factory's pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = factory.delete_cinema_use_case


@pytest.mark.asyncio
async def test_delete_cinema_use_case_returns_configured_use_case() -> None:
    """Verify factory returns delete use case wired to initialized pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        use_case = factory.delete_cinema_use_case
        assert isinstance(use_case, DeleteCinemaUseCase)
        assert use_case.cinema_repository._gateway._pool is mock_database.pool

        await factory.shutdown()


def test_update_cinema_use_case_requires_initialize() -> None:
    """Verify update use case retains factory's pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = factory.update_cinema_use_case


@pytest.mark.asyncio
async def test_update_cinema_use_case_returns_configured_use_case() -> None:
    """Verify factory returns update use case wired to initialized pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        use_case = factory.update_cinema_use_case
        assert isinstance(use_case, UpdateCinemaUseCase)
        assert use_case.cinema_repository._gateway._pool is mock_database.pool

        await factory.shutdown()


def test_list_cinemas_use_case_requires_initialize() -> None:
    """Verify list use case retains factory's pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = factory.list_cinemas_use_case


@pytest.mark.asyncio
async def test_list_cinemas_use_case_returns_configured_use_case() -> None:
    """Verify factory returns list use case wired to initialized pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        use_case = factory.list_cinemas_use_case
        assert isinstance(use_case, ListCinemasUseCase)
        assert use_case.cinema_repository._gateway._pool is mock_database.pool

        await factory.shutdown()


def test_list_cinema_source_assignments_query_requires_initialize() -> None:
    """Verify assignment query retains pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = factory.list_cinema_source_assignments_query


@pytest.mark.asyncio
async def test_list_assignments_query_returns_configured_query() -> None:
    """Verify factory returns assignment query wired to database pool."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()

        query = factory.list_cinema_source_assignments_query
        assert isinstance(query, ListCinemaSourceAssignmentsQuery)
        assert query._reader._pool is mock_database.pool

        await factory.shutdown()


@pytest.mark.parametrize(
    "property_name",
    [
        "create_source_use_case",
        "list_sources_use_case",
        "delete_source_use_case",
        "assign_source_use_case",
        "unassign_source_use_case",
        "get_cinema_source_use_case",
        "get_cinema_use_case",
        "get_cinema_screenings_query",
        "get_cinema_movies_use_case",
        "list_movies_use_case",
        "get_movie_use_case",
        "get_movie_screenings_query",
        "search_screenings_query",
        "get_screening_query",
        "import_screenings_use_case",
    ],
)
def test_configured_use_cases_require_initialize(property_name: str) -> None:
    """Verify configured use cases retain pre-init failure behavior."""
    factory = MarquiseFactory()

    with pytest.raises(RuntimeError, match="Database pool not available"):
        _ = getattr(factory, property_name)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("property_name", "use_case_type"),
    [
        ("create_source_use_case", CreateSourceUseCase),
        ("list_sources_use_case", ListSourcesUseCase),
        ("delete_source_use_case", DeleteSourceUseCase),
        ("assign_source_use_case", AssignSourceUseCase),
        ("unassign_source_use_case", UnassignSourceUseCase),
        ("get_cinema_source_use_case", GetCinemaSourceUseCase),
        ("list_registry_sources_use_case", ListRegistrySourcesUseCase),
        ("get_cinema_use_case", GetCinemaUseCase),
        ("get_cinema_screenings_query", GetCinemaScreeningsQuery),
        ("get_cinema_movies_use_case", GetCinemaMoviesUseCase),
        ("list_movies_use_case", ListMoviesUseCase),
        ("get_movie_use_case", GetMovieUseCase),
        ("get_movie_screenings_query", GetMovieScreeningsQuery),
        ("search_screenings_query", SearchScreeningsQuery),
        ("get_screening_query", GetScreeningQuery),
        ("import_screenings_use_case", ImportScreeningsCommand),
    ],
)
async def test_factory_returns_configured_use_cases(
    property_name: str,
    use_case_type: type,
) -> None:
    """Verify every configured use case is available after initialization."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()
        assert isinstance(getattr(factory, property_name), use_case_type)
        await factory.shutdown()


# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_database_health_pings_database() -> None:
    """Verify check_database_health pings the open database."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()
    mock_database.ping.return_value = True

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        factory = MarquiseFactory()
        await factory.initialize()
        result = await factory.check_database_health()
        assert result is True
        mock_database.ping.assert_awaited_once()
        await factory.shutdown()


@pytest.mark.asyncio
async def test_check_database_health_returns_false_before_init() -> None:
    """Verify check_database_health returns False when not initialized."""
    factory = MarquiseFactory()
    result = await factory.check_database_health()
    assert result is False


# ------------------------------------------------------------------
# Async context manager
# ------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager_lifecycle() -> None:
    """Verify async with initializes and shuts down the factory."""
    mock_database = AsyncMock()
    mock_database.pool = AsyncMock()

    with patch(
        "marquise.infrastructure.di.factory.Database", return_value=mock_database
    ):
        async with MarquiseFactory() as factory:
            assert isinstance(factory.list_cinemas_use_case, ListCinemasUseCase)
            mock_database.connect.assert_awaited_once()

        mock_database.disconnect.assert_awaited_once()
