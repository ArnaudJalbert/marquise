"""Tests for UnassignSourceUseCase InputData and OutputData."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.unassign_source import UnassignSourceUseCase


def test_input_data_rejects_empty_cinema_id() -> None:
    """Verify InputData rejects an empty cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        UnassignSourceUseCase.InputData(cinema_id="")


def test_input_data_rejects_whitespace_cinema_id() -> None:
    """Verify InputData rejects a whitespace-only cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        UnassignSourceUseCase.InputData(cinema_id="   ")


def test_input_data_allows_valid_input() -> None:
    """Verify InputData accepts valid data."""
    data = UnassignSourceUseCase.InputData(cinema_id="cin-001")
    assert data.cinema_id == "cin-001"


def test_output_data_creation() -> None:
    """Verify OutputData can be created."""
    response = UnassignSourceUseCase.OutputData(cinema_id="cin-001")
    assert response.cinema_id == "cin-001"
