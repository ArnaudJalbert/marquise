"""TMDB v3 HTTP transport and pagination, without metadata selection policy."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from http.client import HTTPException, HTTPMessage
from typing import IO
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from marquise.application.metadata import MetadataBatch, MetadataFailure
from marquise.interface_adapters.repositories.protocols.tmdb_metadata_source import (
    TmdbMetadataError,
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> None:
        return None


async def _fetch(url: str, headers: dict[str, str]) -> bytes:
    def read() -> bytes:
        # Never forward the credential-bearing request to a redirect target.
        with build_opener(_NoRedirect()).open(
            Request(url, headers=headers), timeout=10
        ) as response:
            return response.read()

    return await asyncio.to_thread(read)


class TmdbMetadataHttpSource:
    """Fetch JSON using injected credentials and an optional fake transport."""

    def __init__(
        self,
        api_key: str,
        *,
        fetch: Callable[[str, dict[str, str]], Awaitable[bytes]] = _fetch,
    ) -> None:
        self._api_key = api_key
        self._fetch = fetch

    async def get(self, path: str, params: dict[str, str] | None = None) -> dict:
        """Retrieve an endpoint with typed failures and no secret in diagnostics."""
        if not self._api_key.strip():
            raise TmdbMetadataError(
                MetadataFailure("unavailable", "TMDB API key is not configured")
            )
        if not path.startswith(("movie/", "person/", "search/")) or any(
            part in path for part in ("?", "#", "..", ":", "\\")
        ):
            raise TmdbMetadataError(
                MetadataFailure("invalid_data", "Invalid TMDB endpoint")
            )
        query = urlencode({**(params or {}), "api_key": self._api_key})
        url = f"https://api.themoviedb.org/3/{path}?{query}"
        try:
            data = json.loads(await self._fetch(url, {"Accept": "application/json"}))
            if not isinstance(data, dict) or data.get("success") is False:
                raise ValueError("invalid response")
            return data
        except HTTPError as error:
            status = error.code
            kind = (
                "rate_limited"
                if status == 429
                else "not_found"
                if status == 404
                else "unavailable"
            )
            failure = MetadataFailure(
                kind, f"TMDB HTTP {status}", status == 429 or status >= 500
            )
        except (OSError, HTTPException):
            failure = MetadataFailure("unavailable", "TMDB request failed", True)
        except (ValueError, TypeError):
            failure = MetadataFailure("invalid_data", "Invalid TMDB JSON")
        # Raise outside the handler so the original secret-bearing error is absent
        # even from the exception's context, not merely hidden when formatted.
        raise TmdbMetadataError(failure)

    async def pages(self, path: str, params: dict[str, str]) -> MetadataBatch[dict]:
        """Retrieve every page in order, or explicitly return incomplete rows."""
        rows: list[dict] = []
        page = 1
        expected_total: int | None = None
        expected_pages: int | None = None
        while True:
            try:
                data = await self.get(path, {**params, "page": str(page)})
                total = data["total_results"]
                pages = data["total_pages"]
                results = data["results"]
                if (
                    type(total) is not int
                    or total < 0
                    or type(pages) is not int
                    or pages < 0
                    or type(data["page"]) is not int
                    or data["page"] != page
                    or not isinstance(results, list)
                    or not all(isinstance(row, dict) for row in results)
                    or (expected_total is not None and total != expected_total)
                    or (expected_pages is not None and pages != expected_pages)
                    or (total > 0 and (not results or pages < page))
                    or (total == 0 and (results or pages > 1))
                ):
                    raise ValueError("invalid page")
                expected_total, expected_pages = total, pages
                rows.extend(results)
                if page >= pages:
                    if len(rows) != total:
                        raise ValueError("incomplete results")
                    return MetadataBatch(tuple(rows))
                if len(rows) >= total:
                    raise ValueError("inconsistent results")
                page += 1
            except TmdbMetadataError as error:
                return MetadataBatch(tuple(rows), False, error.failure)
            except (KeyError, TypeError, ValueError):
                return MetadataBatch(
                    tuple(rows),
                    False,
                    MetadataFailure("invalid_data", "Invalid TMDB pagination"),
                )
