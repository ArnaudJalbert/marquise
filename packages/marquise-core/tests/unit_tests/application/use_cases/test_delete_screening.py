"""Tests for DeleteScreeningUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.repositories import ScreeningRepository
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.domain.value_objects import ScreeningId


@pytest.mark.asyncio
async def test_deletes_and_returns_id() -> None:
    """A successful hard delete returns the deleted screening ID."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.delete.return_value = True
    use_case = DeleteScreeningUseCase(screening_repository=screening_repo)

    result = await use_case.execute(
        DeleteScreeningUseCase.InputData(screening_id="scr-1")
    )

    assert result.screening_id == "scr-1"
    screening_repo.delete.assert_awaited_once_with(
        screening_id=ScreeningId(value="scr-1")
    )


@pytest.mark.asyncio
async def test_raises_when_screening_missing() -> None:
    """Deleting an unknown screening raises ScreeningNotFoundError."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.delete.return_value = False
    use_case = DeleteScreeningUseCase(screening_repository=screening_repo)

    with pytest.raises(ScreeningNotFoundError, match="scr-missing"):
        await use_case.execute(
            DeleteScreeningUseCase.InputData(screening_id="scr-missing")
        )

    screening_repo.delete.assert_awaited_once_with(
        screening_id=ScreeningId(value="scr-missing")
    )


def test_input_rejects_empty_screening_id() -> None:
    """An empty screening_id is rejected."""
    with pytest.raises(ValueError, match="screening_id must not be empty"):
        DeleteScreeningUseCase.InputData(screening_id="  ")


def test_output_data_creation() -> None:
    """OutputData can be created with the deleted screening ID."""
    response = DeleteScreeningUseCase.OutputData(screening_id="scr-1")
    assert response.screening_id == "scr-1"
