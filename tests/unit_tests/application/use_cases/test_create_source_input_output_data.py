"""Tests for CreateSourceUseCase InputData and OutputData."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.create_source import CreateSourceUseCase


def test_input_data_rejects_empty_name() -> None:
    """Verify InputData rejects an empty name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateSourceUseCase.InputData(name="", display_name="Display")


def test_input_data_rejects_whitespace_name() -> None:
    """Verify InputData rejects a whitespace-only name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateSourceUseCase.InputData(name="   ", display_name="Display")


def test_input_data_rejects_empty_display_name() -> None:
    """Verify InputData rejects an empty display_name."""
    with pytest.raises(ValueError, match="display_name must not be empty"):
        CreateSourceUseCase.InputData(name="source", display_name="")


def test_input_data_rejects_whitespace_display_name() -> None:
    """Verify InputData rejects a whitespace-only display_name."""
    with pytest.raises(ValueError, match="display_name must not be empty"):
        CreateSourceUseCase.InputData(name="source", display_name="   ")


def test_input_data_allows_valid_input() -> None:
    """Verify InputData accepts valid data."""
    data = CreateSourceUseCase.InputData(
        name="cineplex",
        display_name="Cineplex",
        description="Cineplex showtimes",
    )
    assert data.name == "cineplex"
    assert data.display_name == "Cineplex"
    assert data.description == "Cineplex showtimes"


def test_input_data_defaults() -> None:
    """Verify InputData defaults."""
    data = CreateSourceUseCase.InputData(name="source", display_name="Source")
    assert data.description is None


def test_output_data_creation() -> None:
    """Verify OutputData can be created."""
    response = CreateSourceUseCase.OutputData(
        name="cineplex",
        display_name="Cineplex",
        description="A source",
    )
    assert response.name == "cineplex"
    assert response.display_name == "Cineplex"
    assert response.description == "A source"


def test_output_data_rejects_empty_name() -> None:
    """Verify OutputData rejects an empty name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateSourceUseCase.OutputData(name="", display_name="Display")


def test_output_data_rejects_empty_display_name() -> None:
    """Verify OutputData rejects an empty display_name."""
    with pytest.raises(ValueError, match="display_name must not be empty"):
        CreateSourceUseCase.OutputData(name="source", display_name="")
