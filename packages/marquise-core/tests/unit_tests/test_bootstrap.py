"""Tests for the create_factory_session bootstrap API."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from unittest.mock import MagicMock, create_autospec, patch

import asyncpg
import pytest

from marquise.bootstrap import create_factory_session
from marquise.infrastructure.di.factory import MarquiseFactory
from marquise.infrastructure.supabase.database import Database

DATABASE_URL = "postgresql://u:p@localhost:5432/db"


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the database URL and keep any local .env file out of the tests."""
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setattr("marquise.bootstrap.load_dotenv", lambda: True)


@pytest.fixture
def database() -> Iterator[MagicMock]:
    """Provide the database the session opens."""
    connected = create_autospec(Database, instance=True)
    connected.pool = create_autospec(asyncpg.Pool, instance=True)
    with patch("marquise.bootstrap.Database", return_value=connected):
        yield connected


@pytest.mark.asyncio
async def test_session_connects_yields_factory_and_disconnects(
    database: MagicMock,
) -> None:
    """The session opens the database, yields a factory, then closes it."""
    async with create_factory_session() as factory:
        assert isinstance(factory, MarquiseFactory)
        database.connect.assert_awaited_once()
        database.disconnect.assert_not_awaited()

    database.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_disconnects_when_the_caller_fails(database: MagicMock) -> None:
    """A failure inside the session still closes the database."""
    with pytest.raises(RuntimeError, match="command failed"):
        async with create_factory_session():
            raise RuntimeError("command failed")

    database.disconnect.assert_awaited_once()


@pytest.mark.asyncio
async def test_session_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing DATABASE_URL fails before any database is opened."""
    monkeypatch.delenv("DATABASE_URL")
    with (
        patch("marquise.bootstrap.Database") as database_class,
        pytest.raises(RuntimeError, match="DATABASE_URL is required"),
    ):
        async with create_factory_session():
            pass

    database_class.assert_not_called()


@pytest.mark.asyncio
async def test_session_reads_dotenv_before_building_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A database URL found only in .env still reaches the database."""
    monkeypatch.delenv("DATABASE_URL")
    dotenv_url = "postgresql://dotenv@localhost:5432/db"

    def fake_load_dotenv() -> bool:
        monkeypatch.setenv("DATABASE_URL", dotenv_url)
        return True

    monkeypatch.setattr("marquise.bootstrap.load_dotenv", fake_load_dotenv)
    connected = create_autospec(Database, instance=True)
    connected.pool = create_autospec(asyncpg.Pool, instance=True)
    with patch("marquise.bootstrap.Database", return_value=connected) as database:
        async with create_factory_session():
            pass

    assert database.call_args.args[0].database_url == dotenv_url


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
