"""Tests of TMDB search parsing without live HTTP."""

from __future__ import annotations

import json
import traceback
from unittest.mock import AsyncMock

import pytest

from marquise.infrastructure.sources.tmdb import TmdbSearchError, TmdbSearchGateway


@pytest.mark.asyncio
async def test_search_uses_title_and_release_year() -> None:
    """A title/year search returns one candidate and sends both filters."""
    fetch = AsyncMock(
        return_value=json.dumps(
            {
                "total_results": 1,
                "results": [
                    {"id": 42, "title": "Doomsday", "release_date": "2026-12-18"}
                ],
            }
        ).encode()
    )
    gateway = TmdbSearchGateway("key", fetch=fetch)

    results = await gateway.search("Docteur Doom", 2026)

    assert [(r.id, r.title, r.release_year) for r in results] == [
        ("42", "Doomsday", 2026)
    ]
    url, headers = fetch.await_args.args
    assert "query=Docteur+Doom" in url
    assert "primary_release_year=2026" in url
    assert "api_key=key" in url
    assert "Accept" in headers


@pytest.mark.asyncio
async def test_search_returns_no_or_multiple_candidates() -> None:
    """Zero and multiple hits stay distinguishable by list length."""
    fetch = AsyncMock(
        side_effect=[
            json.dumps({"total_results": 0, "results": []}).encode(),
            json.dumps(
                {
                    "total_results": 2,
                    "results": [
                        {"id": 1, "title": "It", "release_date": "1990-01-01"},
                        {"id": 2, "title": "It", "release_date": "2017-01-01"},
                    ],
                }
            ).encode(),
        ]
    )
    gateway = TmdbSearchGateway("key", fetch=fetch)

    assert await gateway.search("Unknown", None) == []
    assert [r.id for r in await gateway.search("It", None)] == ["1", "2"]
    assert "primary_release_year" not in fetch.await_args_list[1].args[0]


@pytest.mark.asyncio
async def test_missing_key_and_network_error_are_explicit() -> None:
    """Bad config or transport errors never become a fabricated no-match."""
    with pytest.raises(TmdbSearchError):
        await TmdbSearchGateway("").search("It", 2017)

    fetch = AsyncMock(side_effect=OSError("network down"))
    with pytest.raises(TmdbSearchError, match="TMDB search failed"):
        await TmdbSearchGateway("key", fetch=fetch).search("It", 2017)


@pytest.mark.asyncio
async def test_rejects_truncated_one_result_page() -> None:
    """A partial page must not turn an ambiguous search into a clear hit."""
    fetch = AsyncMock(
        return_value=json.dumps(
            {"total_results": 2, "results": [{"id": 1, "title": "It"}]}
        ).encode()
    )
    with pytest.raises(TmdbSearchError, match="incomplete"):
        await TmdbSearchGateway("key", fetch=fetch).search("It", None)


@pytest.mark.asyncio
async def test_network_error_traceback_does_not_reveal_api_key() -> None:
    """A failed request cannot print the API key from its URL in a traceback."""
    key = "test-secret-do-not-log"
    fetch = AsyncMock(side_effect=OSError(f"failed https://tmdb/?api_key={key}"))

    with pytest.raises(TmdbSearchError) as error:
        await TmdbSearchGateway(key, fetch=fetch).search("It", None)

    assert key not in "".join(traceback.format_exception(error.value))
