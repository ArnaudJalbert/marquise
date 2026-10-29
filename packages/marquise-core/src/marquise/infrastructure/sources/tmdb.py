"""Fetch plain TMDB movie search responses over its v3 API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from marquise.interface_adapters.repositories.protocols.movie_search_source import (
    MovieSearchError,
)


class TmdbSearchError(MovieSearchError):
    """A TMDB lookup could not be completed."""


async def _fetch(url: str, headers: dict[str, str]) -> bytes:
    """Run the blocking standard-library HTTP call off the event loop."""

    def read() -> bytes:
        with urlopen(Request(url, headers=headers), timeout=10) as response:
            return response.read()

    return await asyncio.to_thread(read)


class TmdbSource:
    """Fetch a TMDB response without mapping it to movie identities."""

    def __init__(
        self,
        api_key: str,
        *,
        fetch: Callable[[str, dict[str, str]], Awaitable[bytes]] = _fetch,
    ) -> None:
        self._api_key = api_key
        self._fetch = fetch

    async def search(self, title: str, year: int | None) -> dict:
        """Return plain JSON data, or fail without leaking the API key."""
        if not self._api_key:
            raise TmdbSearchError("TMDB_API_KEY is not configured")
        params = {"query": title, "api_key": self._api_key, "language": "en-US"}
        if year is not None:
            params["primary_release_year"] = str(year)
        url = "https://api.themoviedb.org/3/search/movie?" + urlencode(params)
        try:
            body = await self._fetch(url, {"Accept": "application/json"})
            data = json.loads(body)
            if not isinstance(data, dict):
                raise ValueError("expected JSON object")
            return data
        except (OSError, ValueError, TypeError):
            # HTTP errors may include the request URL and its API key.
            raise TmdbSearchError("TMDB search failed") from None
