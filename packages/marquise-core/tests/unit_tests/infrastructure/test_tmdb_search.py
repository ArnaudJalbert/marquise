"""TMDB HTTP source tests without live requests."""

from __future__ import annotations

import json
import traceback
from unittest.mock import AsyncMock

import pytest

from marquise.infrastructure.sources.tmdb import TmdbSearchError, TmdbSource


@pytest.mark.asyncio
async def test_source_queries_tmdb_by_title_and_year() -> None:
    """The source sends both filters and returns unmapped response data."""
    payload = {"total_results": 1, "results": [{"id": 42, "title": "Doomsday"}]}
    fetch = AsyncMock(return_value=json.dumps(payload).encode())

    result = await TmdbSource("key", fetch=fetch).search("Docteur Doom", 2026)

    assert result == payload
    url, headers = fetch.await_args.args
    assert "query=Docteur+Doom" in url
    assert "primary_release_year=2026" in url
    assert "api_key=key" in url
    assert "Accept" in headers


@pytest.mark.asyncio
async def test_source_omits_unknown_year() -> None:
    """The source does not send a year filter when the source has no year."""
    fetch = AsyncMock(return_value=b'{"results": [], "total_results": 0}')

    assert await TmdbSource("key", fetch=fetch).search("It", None) == {
        "results": [],
        "total_results": 0,
    }
    assert "primary_release_year" not in fetch.await_args.args[0]


@pytest.mark.asyncio
async def test_missing_key_and_network_error_are_explicit() -> None:
    """Missing credentials and transport failures are not no-match results."""
    with pytest.raises(TmdbSearchError):
        await TmdbSource("").search("It", 2017)

    fetch = AsyncMock(side_effect=OSError("network down"))
    with pytest.raises(TmdbSearchError, match="TMDB search failed"):
        await TmdbSource("key", fetch=fetch).search("It", 2017)


@pytest.mark.asyncio
async def test_network_error_traceback_does_not_reveal_api_key() -> None:
    """An HTTP error cannot print the API key from its URL in a traceback."""
    key = "test-secret-do-not-log"
    fetch = AsyncMock(side_effect=OSError(f"failed https://tmdb/?api_key={key}"))

    with pytest.raises(TmdbSearchError) as error:
        await TmdbSource(key, fetch=fetch).search("It", None)

    assert key not in "".join(traceback.format_exception(error.value))
