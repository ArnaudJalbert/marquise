"""Tests for GetCinemaSourceUseCase InputData and OutputData."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase


def test_input_data_rejects_empty_cinema_id() -> None:
    """Verify InputData rejects an empty cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        GetCinemaSourceUseCase.InputData(cinema_id="")


def test_input_data_rejects_whitespace_cinema_id() -> None:
    """Verify InputData rejects a whitespace-only cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        GetCinemaSourceUseCase.InputData(cinema_id="   ")


def test_input_data_allows_valid_input() -> None:
    """Verify InputData accepts valid data."""
    data = GetCinemaSourceUseCase.InputData(cinema_id="cin-001")
    assert data.cinema_id == "cin-001"


def test_output_data_creation() -> None:
    """Verify OutputData can be created."""
    response = GetCinemaSourceUseCase.OutputData(
        cinema_id="cin-001",
        source_name="cineplex",
        source_display_name="Cineplex",
    )
    assert response.cinema_id == "cin-001"
    assert response.source_name == "cineplex"
    assert response.source_display_name == "Cineplex"
