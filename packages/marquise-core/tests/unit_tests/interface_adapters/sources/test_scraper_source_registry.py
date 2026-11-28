"""Unit tests for ScraperSourceRegistry."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.interface_adapters.sources.base import (
    SourceAdapter,
)
from marquise.interface_adapters.sources.scraper_source_registry import (
    ScraperSourceRegistry,
)


@pytest.fixture
def registry() -> ScraperSourceRegistry:
    """Provide an empty ScraperSourceRegistry."""
    return ScraperSourceRegistry()


@pytest.fixture
def mock_adapter() -> SourceAdapter:
    """Provide a mocked SourceAdapter."""
    return create_autospec(SourceAdapter, instance=True)


def test_register_raises_on_duplicate_name(
    registry: ScraperSourceRegistry, mock_adapter: SourceAdapter
) -> None:
    """Verify register raises ValueError when name is already registered."""
    registry.register("cinemacinema", mock_adapter)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("cinemacinema", mock_adapter)


def test_list_available_returns_all_registered(
    registry: ScraperSourceRegistry, mock_adapter: SourceAdapter
) -> None:
    """Verify list_available returns the names of all registered sources."""
    mock_adapter2 = create_autospec(SourceAdapter, instance=True)
    registry.register("cinemacinema", mock_adapter)
    registry.register("cinema_du_parc", mock_adapter2)

    available = registry.list_available()

    assert available == ["cinemacinema", "cinema_du_parc"]


def test_list_available_returns_empty_when_none_registered(
    registry: ScraperSourceRegistry,
) -> None:
    """Verify list_available returns an empty list when nothing is registered."""
    assert registry.list_available() == []
