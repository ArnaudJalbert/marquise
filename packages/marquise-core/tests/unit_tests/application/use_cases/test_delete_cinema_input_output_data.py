"""Tests for DeleteCinemaUseCase InputData/OutputData."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase


def test_input_data_rejects_empty_cinema_id() -> None:
    """Verify InputData rejects an empty cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        DeleteCinemaUseCase.InputData(cinema_id="")


def test_input_data_rejects_whitespace_cinema_id() -> None:
    """Verify InputData rejects a whitespace-only cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        DeleteCinemaUseCase.InputData(cinema_id="   ")
