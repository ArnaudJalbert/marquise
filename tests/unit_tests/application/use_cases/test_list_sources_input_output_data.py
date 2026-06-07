"""Tests for ListSourcesUseCase InputData and OutputData."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.list_sources import ListSourcesUseCase


def test_input_data_creation() -> None:
    """Verify InputData can be created (no parameters)."""
    data = ListSourcesUseCase.InputData()
    assert data is not None


def test_source_data_creation() -> None:
    """Verify SourceData can be created with valid data."""
    data = ListSourcesUseCase.SourceData(
        name="cineplex",
        display_name="Cineplex",
        description="A source",
    )
    assert data.name == "cineplex"
    assert data.display_name == "Cineplex"


def test_source_data_rejects_empty_name() -> None:
    """Verify SourceData rejects an empty name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        ListSourcesUseCase.SourceData(name="", display_name="Display")


def test_source_data_rejects_empty_display_name() -> None:
    """Verify SourceData rejects an empty display_name."""
    with pytest.raises(ValueError, match="display_name must not be empty"):
        ListSourcesUseCase.SourceData(name="source", display_name="")


def test_source_data_allows_none_description() -> None:
    """Verify SourceData allows None description."""
    data = ListSourcesUseCase.SourceData(name="source", display_name="Source")
    assert data.description is None


def test_output_data_creation() -> None:
    """Verify OutputData can be created."""
    source = ListSourcesUseCase.SourceData(name="s", display_name="S")
    output = ListSourcesUseCase.OutputData(sources=[source])
    assert len(output.sources) == 1


def test_output_data_empty_list() -> None:
    """Verify OutputData with empty sources list."""
    output = ListSourcesUseCase.OutputData(sources=[])
    assert output.sources == []


def test_output_data_rejects_none_sources() -> None:
    """Verify OutputData rejects None for sources."""
    with pytest.raises(ValueError, match="sources must not be None"):
        ListSourcesUseCase.OutputData(sources=None)  # type: ignore
