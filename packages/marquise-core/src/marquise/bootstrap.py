"""Public bootstrap API that opens a factory session."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv

from marquise.infrastructure.di.factory import MarquiseFactory
from marquise.infrastructure.supabase.config.settings import Settings
from marquise.infrastructure.supabase.database import Database


def _read_settings() -> Settings:
    """Load a local .env file, then read settings from the environment."""
    load_dotenv()
    return Settings(
        database_url=os.environ.get("DATABASE_URL", ""),
        cineplex_api_key=os.environ.get("CINEPLEX_API_KEY", ""),
        tmdb_api_key=os.environ.get("TMDB_API_KEY", ""),
        schema=os.environ.get("DATABASE_SCHEMA", "marquise"),
    )


async def _connect_database(settings: Settings) -> Database:
    """Open the database connection pool.

    Args:
        settings: Settings that hold the database URL.

    Returns:
        The connected database.

    Raises:
        RuntimeError: If DATABASE_URL is not configured.
    """
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")
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
        RuntimeError: If DATABASE_URL is not configured.

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
