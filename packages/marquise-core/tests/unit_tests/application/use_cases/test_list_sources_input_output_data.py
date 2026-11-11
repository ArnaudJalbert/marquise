"""Tests for ListSourcesUseCase InputData and OutputData."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.list_sources import ListSourcesUseCase


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
