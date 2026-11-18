"""Public bootstrap API that opens a factory session."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv

from marquise.infrastructure.di.factory import MarquiseFactory
from marquise.infrastructure.supabase.config.settings import Settings
from marquise.infrastructure.supabase.database import Database

_REQUIRED_VARIABLES = ("DATABASE_URL", "DATABASE_SCHEMA", "TMDB_API_KEY")


def _require_variables() -> None:
    """Check that every required environment variable is set and not empty.

    Raises:
        RuntimeError: Naming every required variable that is unset or empty.
    """
    missing = [name for name in _REQUIRED_VARIABLES if not os.environ.get(name)]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(f"Missing required environment variables: {names}")


def _read_settings() -> Settings:
    """Load a local .env file, then read settings from the environment.

    Returns:
        Settings built from the required environment variables.

    Raises:
        RuntimeError: If a required variable is unset or empty.
    """
    load_dotenv()
    _require_variables()
    return Settings(
        database_url=os.environ["DATABASE_URL"],
        tmdb_api_key=os.environ["TMDB_API_KEY"],
        schema=os.environ["DATABASE_SCHEMA"],
    )


async def _connect_database(settings: Settings) -> Database:
    """Open the database connection pool.

    Args:
        settings: Settings that hold the database URL.

    Returns:
        The connected database.
    """
    database = Database(settings)
    await database.connect()
    return database


@asynccontextmanager
async def create_factory_session() -> AsyncGenerator[MarquiseFactory]:
    """Open the database, yield a wired factory, then close the database.

    This is the only way to get a MarquiseFactory, so every caller closes the
    database it opened.

    Yields:
        A factory whose use cases share the open database pool.

    Raises:
        RuntimeError: If DATABASE_URL, DATABASE_SCHEMA or TMDB_API_KEY is
            unset or empty. Nothing is opened.

    Example:
        async with create_factory_session() as factory:
            use_case = factory.cinemas.list_cinemas_use_case
            result = await use_case.execute(use_case.InputData(page=1, size=50))
    """
    settings = _read_settings()
    database = await _connect_database(settings)
    try:
        yield MarquiseFactory(settings, database)
    finally:
        await database.disconnect()
