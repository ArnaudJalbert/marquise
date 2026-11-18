"""Unit tests for the movie-first screening read gateway's paging."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest

from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.infrastructure.supabase.gateways.screening_movie_reader import (
    SupabaseScreeningMovieReadGateway,
)


@pytest.mark.asyncio
async def test_search_binds_page_limit_and_offset() -> None:
    """Page 3 of size 24 binds the page window as the last two SQL arguments."""
    connection = MagicMock(spec=asyncpg.Connection)
    connection.fetch = AsyncMock(return_value=[{"total": 0, "id": None}])
    pool = MagicMock(spec=asyncpg.Pool)

    @asynccontextmanager
    async def acquire() -> AsyncIterator[asyncpg.Connection]:
        yield connection

    pool.acquire = acquire
    now = datetime(2026, 11, 1, tzinfo=UTC)
    gateway = SupabaseScreeningMovieReadGateway(pool, "public")

    await gateway.search(ScreeningMovieReader.SearchRequest(now, None, now, 3, 24))

    assert connection.fetch.await_args.args[-2:] == (24, 48)
