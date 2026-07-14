"""Tests for ListRegistrySourcesUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import RegistrySourceEntry, SourceRegistryQuery
from marquise.application.use_cases import ListRegistrySourcesUseCase


@pytest.mark.asyncio
async def test_list_registry_sources_returns_all() -> None:
    """Verify list_registry_sources returns all entries from the registry."""
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_registry.list_available.return_value = {
        "cinemacinema": RegistrySourceEntry(name="cinemacinema"),
        "cineplex": RegistrySourceEntry(name="cineplex"),
    }

    use_case = ListRegistrySourcesUseCase(registry=mock_registry)
    request = ListRegistrySourcesUseCase.InputData()

    response = await use_case.execute(request)

    assert len(response.sources) == 2
    assert response.sources[0].name == "cinemacinema"
    assert response.sources[1].name == "cineplex"
    mock_registry.list_available.assert_called_once()


@pytest.mark.asyncio
async def test_list_registry_sources_returns_empty() -> None:
    """Verify list_registry_sources returns empty list when registry is empty."""
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)
    mock_registry.list_available.return_value = {}

    use_case = ListRegistrySourcesUseCase(registry=mock_registry)
    request = ListRegistrySourcesUseCase.InputData()

    response = await use_case.execute(request)

    assert response.sources == []


def test_source_entry_raises_on_empty_name() -> None:
    """Verify SourceEntry.__post_init__ rejects empty name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        ListRegistrySourcesUseCase.SourceEntry(name="")


def test_input_data_creation() -> None:
    """Verify InputData can be created with no parameters."""
    data = ListRegistrySourcesUseCase.InputData()
    assert data is not None
