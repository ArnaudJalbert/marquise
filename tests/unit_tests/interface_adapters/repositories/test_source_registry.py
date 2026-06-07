"""Unit tests for SourceRegistry."""

from __future__ import annotations

from typing import Any
from unittest.mock import create_autospec

import pytest

from marquise.interface_adapters.repositories.protocols.showtime_source import (
    ShowtimeSource,
)
from marquise.interface_adapters.repositories.source_registry import SourceRegistry


@pytest.fixture
def registry() -> SourceRegistry:
    """Provide an empty SourceRegistry."""
    return SourceRegistry()


@pytest.fixture
def mock_source() -> ShowtimeSource:
    """Provide a mocked ShowtimeSource subclass."""
    source = create_autospec(ShowtimeSource, instance=True)
    source.fetch_showtimes = _fake_fetch
    return source


async def _fake_fetch(self: ShowtimeSource, cinema_name: str) -> list[dict[str, Any]]:  # noqa: ANN401
    """Fake fetch for testing."""
    return []


def test_register_adds_source(
    registry: SourceRegistry, mock_source: ShowtimeSource
) -> None:
    """Verify register adds a source that can be retrieved with get."""
    registry.register("cinemacinema", mock_source)
    assert registry.get("cinemacinema") is mock_source


def test_get_raises_key_error_for_unregistered_name(
    registry: SourceRegistry,
) -> None:
    """Verify get raises KeyError when name is not registered."""
    with pytest.raises(KeyError, match="No source registered"):
        registry.get("unknown")


def test_register_raises_on_duplicate_name(
    registry: SourceRegistry, mock_source: ShowtimeSource
) -> None:
    """Verify register raises ValueError when name is already registered."""
    registry.register("cinemacinema", mock_source)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("cinemacinema", mock_source)


def test_register_multiple_sources(
    registry: SourceRegistry, mock_source: ShowtimeSource
) -> None:
    """Verify multiple sources can be registered and retrieved independently."""
    mock_source2 = create_autospec(ShowtimeSource, instance=True)
    mock_source2.fetch_showtimes = _fake_fetch
    registry.register("cinemacinema", mock_source)
    registry.register("cinema_du_parc", mock_source2)
    assert registry.get("cinemacinema") is mock_source
    assert registry.get("cinema_du_parc") is mock_source2


def test_list_available_returns_all_registered(
    registry: SourceRegistry, mock_source: ShowtimeSource
) -> None:
    """Verify list_available returns all registered sources with metadata."""
    mock_source2 = create_autospec(ShowtimeSource, instance=True)
    mock_source2.fetch_showtimes = _fake_fetch
    registry.register("cinemacinema", mock_source)
    registry.register("cinema_du_parc", mock_source2)

    available = registry.list_available()

    assert len(available) == 2
    assert "cinemacinema" in available
    assert "cinema_du_parc" in available
    entry = available["cinemacinema"]
    assert entry.name == "cinemacinema"


def test_list_available_returns_empty_when_none_registered(
    registry: SourceRegistry,
) -> None:
    """Verify list_available returns empty dict when nothing is registered."""
    assert registry.list_available() == {}
