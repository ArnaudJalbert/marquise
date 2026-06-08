"""Unit tests for SourceRegistry."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.interface_adapters.repositories.source_adapters.base import (
    SourceAdapter,
)
from marquise.interface_adapters.repositories.source_registry import SourceRegistry


@pytest.fixture
def registry() -> SourceRegistry:
    """Provide an empty SourceRegistry."""
    return SourceRegistry()


@pytest.fixture
def mock_adapter() -> SourceAdapter:
    """Provide a mocked SourceAdapter."""
    return create_autospec(SourceAdapter, instance=True)


def test_register_adds_adapter(
    registry: SourceRegistry, mock_adapter: SourceAdapter
) -> None:
    """Verify register adds an adapter that appears in list_available."""
    registry.register("cinemacinema", mock_adapter)
    available = registry.list_available()
    assert "cinemacinema" in available


def test_register_raises_on_duplicate_name(
    registry: SourceRegistry, mock_adapter: SourceAdapter
) -> None:
    """Verify register raises ValueError when name is already registered."""
    registry.register("cinemacinema", mock_adapter)
    with pytest.raises(ValueError, match="already registered"):
        registry.register("cinemacinema", mock_adapter)


def test_register_multiple_sources(
    registry: SourceRegistry, mock_adapter: SourceAdapter
) -> None:
    """Verify multiple adapters can be registered independently."""
    mock_adapter2 = create_autospec(SourceAdapter, instance=True)
    registry.register("cinemacinema", mock_adapter)
    registry.register("cinema_du_parc", mock_adapter2)

    available = registry.list_available()
    assert len(available) == 2
    assert "cinemacinema" in available
    assert "cinema_du_parc" in available


def test_list_available_returns_all_registered(
    registry: SourceRegistry, mock_adapter: SourceAdapter
) -> None:
    """Verify list_available returns all registered sources with metadata."""
    mock_adapter2 = create_autospec(SourceAdapter, instance=True)
    registry.register("cinemacinema", mock_adapter)
    registry.register("cinema_du_parc", mock_adapter2)

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
