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
