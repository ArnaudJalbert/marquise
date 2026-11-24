"""Unit tests for the movie-first screening read gateway's paging."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import create_autospec

import asyncpg
import pytest

from marquise.application.readers.screening_movie_reader import ScreeningMovieReader
from marquise.infrastructure.postgres.gateways.screening_movie_reader import (
    PostgresScreeningMovieReadGateway,
)


@pytest.mark.asyncio
async def test_search_binds_page_limit_and_offset() -> None:
    """Page 3 of size 24 binds the page window as the last two SQL arguments."""
    connection = create_autospec(asyncpg.Connection, instance=True)
    connection.fetch.return_value = [{"total": 0, "id": None}]
    pool = create_autospec(asyncpg.Pool, instance=True)

    @asynccontextmanager
    async def acquire() -> AsyncIterator[asyncpg.Connection]:
        yield connection

    pool.acquire.side_effect = acquire
    now = datetime(2026, 11, 1, tzinfo=UTC)
    gateway = PostgresScreeningMovieReadGateway(pool, "public")

    await gateway.search(ScreeningMovieReader.SearchRequest(now, None, now, 3, 24))

    assert connection.fetch.await_args.args[-2:] == (24, 48)
