"""Tests for the Cineplex subscription key the showtime source sends.

Key discovery and the API call are patched, so no network is used.
"""

from __future__ import annotations

from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from marquise.infrastructure.sources.cineplex.gateways.source import CineplexSource

_MODULE = "marquise.infrastructure.sources.cineplex.gateways.source"


@pytest.fixture
def discover_key() -> Iterator[MagicMock]:
    """Stand in for scraping the key from the Cineplex frontend."""
    with patch(f"{_MODULE}._discover_subscription_key", autospec=True) as discover:
        yield discover


@pytest.fixture
def fetch_json() -> Iterator[MagicMock]:
    """Stand in for the theatrical API call."""
    with patch(f"{_MODULE}._fetch_json", autospec=True, return_value=[]) as fetch:
        yield fetch


@pytest.mark.asyncio
async def test_fetch_showtimes_fails_when_no_key_was_ever_discovered(
    discover_key: MagicMock, fetch_json: MagicMock
) -> None:
    """A failed first discovery raises instead of calling the API."""
    discover_key.return_value = None

    with pytest.raises(RuntimeError, match="Cineplex subscription key discovery"):
        await CineplexSource().fetch_showtimes(location_id=9172)

    fetch_json.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_showtimes_reuses_the_last_discovered_key(
    discover_key: MagicMock, fetch_json: MagicMock
) -> None:
    """A failed discovery after a successful one sends the earlier key."""
    discover_key.side_effect = ["discovered-key", None]
    source = CineplexSource()

    await source.fetch_showtimes(location_id=9172)
    await source.fetch_showtimes(location_id=9172)

    sent_keys = [call.kwargs["api_key"] for call in fetch_json.call_args_list]
    assert sent_keys == ["discovered-key", "discovered-key"]
