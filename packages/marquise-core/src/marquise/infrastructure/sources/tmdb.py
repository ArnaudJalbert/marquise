"""TMDB title search over its v3 API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from marquise.application.repositories.tmdb_search import TmdbCandidate, TmdbSearch


class TmdbSearchError(Exception):
    """A TMDB lookup could not be completed."""


async def _fetch(url: str, headers: dict[str, str]) -> bytes:
    """Run the blocking standard-library HTTP call off the event loop."""

    def read() -> bytes:
        with urlopen(Request(url, headers=headers), timeout=10) as response:
            return response.read()

    return await asyncio.to_thread(read)


class TmdbSearchGateway(TmdbSearch):
    """Search TMDB without leaking its key in errors."""

    def __init__(
        self,
        api_key: str,
        *,
        fetch: Callable[[str, dict[str, str]], Awaitable[bytes]] = _fetch,
    ) -> None:
        self._api_key = api_key
        self._fetch = fetch

    async def search(self, title: str, year: int | None) -> list[TmdbCandidate]:
        """Return candidate films, or fail without mistaking errors for no hits."""
        if not self._api_key:
            raise TmdbSearchError("TMDB_API_KEY is not configured")
        params = {"query": title, "api_key": self._api_key, "language": "en-US"}
        if year is not None:
            params["primary_release_year"] = str(year)
        url = "https://api.themoviedb.org/3/search/movie?" + urlencode(params)
        try:
            body = await self._fetch(url, {"Accept": "application/json"})
            data = json.loads(body)
            results = data["results"]
            if data["total_results"] > len(results) and len(results) == 1:
                raise TmdbSearchError("incomplete TMDB search results")
            return [
                TmdbCandidate(
                    id=str(row["id"]),
                    title=row["title"],
                    release_year=int(row["release_date"][:4])
                    if row.get("release_date")
                    else None,
                )
                for row in results
            ]
        except TmdbSearchError:
            raise
        except (OSError, ValueError, KeyError, TypeError):
            # HTTP errors may include the request URL and its API key.
            raise TmdbSearchError("TMDB search failed") from None
