"""Tests for SourceDefinition entity."""

from __future__ import annotations

import pytest

from marquise.domain.entities import SourceDefinition
from marquise.domain.value_objects import SourceName


def test_source_definition_creation() -> None:
    """Verify SourceDefinition can be created with all fields."""
    source = SourceDefinition(
        name=SourceName(value="cineplex"),
        display_name="Cineplex",
        description="Cineplex cinemas showtime source",
    )
    assert source.name == SourceName(value="cineplex")
    assert source.display_name == "Cineplex"
    assert source.description == "Cineplex cinemas showtime source"


def test_source_definition_minimal_fields() -> None:
    """Verify SourceDefinition can be created with only required fields."""
    source = SourceDefinition(
        name=SourceName(value="cineplex"),
        display_name="Cineplex",
    )
    assert source.description is None


def test_source_definition_rejects_empty_source_name() -> None:
    """Verify creating with empty source name raises ValueError."""
    with pytest.raises(ValueError, match="value must not be empty or whitespace-only"):
        SourceDefinition(
            name=SourceName(value="  "),
            display_name="Cineplex",
        )


def test_source_definition_rejects_empty_display_name() -> None:
    """Verify creating with empty display_name raises ValueError."""
    with pytest.raises(ValueError, match="Source display_name cannot be empty"):
        SourceDefinition(
            name=SourceName(value="cineplex"),
            display_name="  ",
        )
