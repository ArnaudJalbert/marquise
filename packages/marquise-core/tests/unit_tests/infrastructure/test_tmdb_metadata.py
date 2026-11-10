"""Deterministic TMDB transport, failure, pagination and secret handling checks."""

import json
import traceback
from http.client import BadStatusLine, HTTPMessage, IncompleteRead
from io import BytesIO
from unittest.mock import AsyncMock
from urllib.error import HTTPError
from urllib.request import Request

import pytest

from marquise.infrastructure.sources.tmdb_metadata import (
    TmdbMetadataHttpSource,
    _NoRedirect,
)
from marquise.interface_adapters.repositories.protocols.tmdb_metadata_source import (
    TmdbMetadataError,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,kind,retryable",
    [
        (404, "not_found", False),
        (429, "rate_limited", True),
        (503, "unavailable", True),
        (401, "unavailable", False),
        (302, "unavailable", False),
    ],
)
async def test_http_failure_is_typed_and_redacts_context(
    status: int, kind: str, retryable: bool
) -> None:
    """HTTP status survives, while URLs, keys and bodies stay out of diagnostics."""
    secret = "private-test-key"
    error = HTTPError(f"https://tmdb/?api_key={secret}", status, secret, {}, None)
    source = TmdbMetadataHttpSource(secret, fetch=AsyncMock(side_effect=error))
    with pytest.raises(TmdbMetadataError) as caught:
        await source.get("movie/42")
    assert caught.value.failure.kind == kind
    assert caught.value.failure.retryable is retryable
    assert caught.value.__context__ is None
    assert secret not in "".join(traceback.format_exception(caught.value))
    assert secret not in repr(caught.value.failure)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        b"[]",
        b"null",
        b"not-json",
        b"\xff",
        b'{"success": false, "status_message": "secret"}',
    ],
)
async def test_invalid_json_is_not_successful_absence(body: bytes) -> None:
    """Invalid or provider-declared failed responses produce invalid_data."""
    source = TmdbMetadataHttpSource("key", fetch=AsyncMock(return_value=body))
    with pytest.raises(TmdbMetadataError) as caught:
        await source.get("movie/42")
    assert caught.value.failure.kind == "invalid_data"
    assert not caught.value.failure.retryable
    assert "secret" not in str(caught.value)


@pytest.mark.asyncio
async def test_missing_credentials_and_bad_endpoint_make_no_request() -> None:
    """Missing keys and invalid paths fail before sending credentials."""
    fetch = AsyncMock()
    with pytest.raises(TmdbMetadataError):
        await TmdbMetadataHttpSource("", fetch=fetch).get("movie/42")
    with pytest.raises(TmdbMetadataError):
        await TmdbMetadataHttpSource("key", fetch=fetch).get("https://evil.test")
    fetch.assert_not_awaited()


def test_redirect_handler_rejects_credential_forwarding() -> None:
    """Even an HTTP redirect cannot forward the API key to a different host."""
    assert (
        _NoRedirect().redirect_request(
            Request("https://api.themoviedb.org/3/movie/42?api_key=secret"),
            BytesIO(),
            302,
            "Found",
            HTTPMessage(),
            "https://evil.test",
        )
        is None
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "second",
    [
        {"page": 1, "total_pages": 2, "total_results": 2, "results": [{"id": 2}]},
        {"page": 2, "total_pages": 2, "total_results": 3, "results": [{"id": 2}]},
        {"page": 2, "total_pages": 2, "total_results": 2, "results": []},
        {"page": 2, "total_pages": 2, "total_results": 2, "results": [None]},
        {
            "page": 2,
            "total_pages": 2,
            "total_results": 2,
            "results": [{"id": 2}, {"id": 3}],
        },
    ],
)
async def test_invalid_pagination_retains_rows_and_incompleteness(second: dict) -> None:
    """Changed counts, wrong pages and malformed rows never claim completeness."""
    first = {"page": 1, "total_pages": 2, "total_results": 2, "results": [{"id": 1}]}
    fetch = AsyncMock(
        side_effect=[json.dumps(first).encode(), json.dumps(second).encode()]
    )
    result = await TmdbMetadataHttpSource("key", fetch=fetch).pages("search/movie", {})
    assert not result.complete and result.failure.kind == "invalid_data"
    assert result.items[0] == {"id": 1}


@pytest.mark.asyncio
async def test_complete_empty_search_is_distinct_from_failure() -> None:
    """A provider's empty exhaustive search is successful and has no failure."""
    fetch = AsyncMock(
        return_value=json.dumps(
            {"page": 1, "total_pages": 0, "total_results": 0, "results": []}
        ).encode()
    )
    result = await TmdbMetadataHttpSource("key", fetch=fetch).pages("search/person", {})
    assert result.complete and result.failure is None and result.items == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [IncompleteRead(b"private-test-key", 100), BadStatusLine("private-test-key")],
)
async def test_http_protocol_failure_is_retryable_and_sanitized(
    error: IncompleteRead | BadStatusLine,
) -> None:
    """Truncated bodies and malformed HTTP status cannot escape the failure port."""
    fetch = AsyncMock(side_effect=error)
    source = TmdbMetadataHttpSource("private-test-key", fetch=fetch)
    with pytest.raises(TmdbMetadataError) as caught:
        await source.get("movie/42")
    assert caught.value.failure.kind == "unavailable"
    assert caught.value.failure.retryable
    assert caught.value.__context__ is None
    assert "private-test-key" not in "".join(traceback.format_exception(caught.value))


@pytest.mark.asyncio
@pytest.mark.parametrize("body", [b"not-json", b"[]", b'{"success": false}'])
async def test_malformed_json_names_its_check_without_the_body(body: bytes) -> None:
    """A malformed response names malformed_json and never repeats the body."""
    source = TmdbMetadataHttpSource(
        "private-test-key", fetch=AsyncMock(return_value=body)
    )
    with pytest.raises(TmdbMetadataError) as caught:
        await source.get("movie/42")
    failure = caught.value.failure
    assert failure.reason == "malformed_json"
    assert "malformed_json" in failure.message
    assert body.decode() not in failure.message
    assert "private-test-key" not in repr(failure)
    assert "api.themoviedb.org" not in repr(failure)


@pytest.mark.asyncio
async def test_rejected_endpoint_names_its_check_without_the_path() -> None:
    """A rejected endpoint names endpoint_check and never repeats the URL."""
    source = TmdbMetadataHttpSource("private-test-key", fetch=AsyncMock())
    with pytest.raises(TmdbMetadataError) as caught:
        await source.get("https://evil.test/movie")
    failure = caught.value.failure
    assert failure.reason == "endpoint_check"
    assert "endpoint_check" in failure.message
    assert "evil.test" not in repr(failure)
    assert "private-test-key" not in repr(failure)


@pytest.mark.asyncio
async def test_inconsistent_page_names_pagination_without_the_body() -> None:
    """A page with drifting counts names pagination and never repeats the body."""
    page = {"page": 2, "total_pages": 1, "total_results": 1, "results": [{"id": 1}]}
    fetch = AsyncMock(return_value=json.dumps(page).encode())
    source = TmdbMetadataHttpSource("private-test-key", fetch=fetch)
    result = await source.pages("search/movie", {"query": "Twin Peaks"})
    assert result.failure.kind == "invalid_data"
    assert result.failure.reason == "pagination"
    assert "pagination" in result.failure.message
    assert "results" not in repr(result.failure)
    assert "private-test-key" not in repr(result.failure)
