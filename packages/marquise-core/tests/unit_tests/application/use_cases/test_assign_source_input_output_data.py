"""Tests for AssignSourceUseCase InputData and OutputData."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.assign_source import AssignSourceUseCase


def test_input_data_rejects_empty_cinema_id() -> None:
    """Verify InputData rejects an empty cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        AssignSourceUseCase.InputData(cinema_id="", source_name="cineplex")


def test_input_data_rejects_whitespace_cinema_id() -> None:
    """Verify InputData rejects a whitespace-only cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        AssignSourceUseCase.InputData(cinema_id="   ", source_name="cineplex")


def test_input_data_rejects_empty_source_name() -> None:
    """Verify InputData rejects an empty source_name."""
    with pytest.raises(ValueError, match="source_name must not be empty"):
        AssignSourceUseCase.InputData(cinema_id="cin-001", source_name="")


def test_input_data_rejects_whitespace_source_name() -> None:
    """Verify InputData rejects a whitespace-only source_name."""
    with pytest.raises(ValueError, match="source_name must not be empty"):
        AssignSourceUseCase.InputData(cinema_id="cin-001", source_name="   ")


def test_input_data_allows_valid_input() -> None:
    """Verify InputData accepts valid data."""
    data = AssignSourceUseCase.InputData(cinema_id="cin-001", source_name="cineplex")
    assert data.cinema_id == "cin-001"
    assert data.source_name == "cineplex"


def test_output_data_creation() -> None:
    """Verify OutputData can be created."""
    response = AssignSourceUseCase.OutputData(
        cinema_id="cin-001", source_name="cineplex"
    )
    assert response.cinema_id == "cin-001"
    assert response.source_name == "cineplex"
