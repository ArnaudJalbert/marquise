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


def test_input_data_defaults() -> None:
    """Verify InputData defaults."""
    data = CreateSourceUseCase.InputData(name="source", display_name="Source")
    assert data.description is None
