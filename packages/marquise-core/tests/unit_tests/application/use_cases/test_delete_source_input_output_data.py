"""Tests for DeleteSourceUseCase InputData and OutputData."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.delete_source import DeleteSourceUseCase


def test_input_data_rejects_empty_source_name() -> None:
    """Verify InputData rejects an empty source_name."""
    with pytest.raises(ValueError, match="source_name must not be empty"):
        DeleteSourceUseCase.InputData(source_name="")


def test_input_data_rejects_whitespace_source_name() -> None:
    """Verify InputData rejects a whitespace-only source_name."""
    with pytest.raises(ValueError, match="source_name must not be empty"):
        DeleteSourceUseCase.InputData(source_name="   ")
