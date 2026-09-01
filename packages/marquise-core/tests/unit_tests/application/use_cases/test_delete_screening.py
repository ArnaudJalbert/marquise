"""Tests for DeleteScreeningUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.repositories import ScreeningRepository
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.domain.value_objects import ScreeningId


@pytest.fixture
def screening_repository() -> ScreeningRepository:
    """Provide an autospecced screening repository for delete tests."""
    return create_autospec(ScreeningRepository, instance=True)


@pytest.fixture
def use_case(screening_repository: ScreeningRepository) -> DeleteScreeningUseCase:
    """Provide a configured delete-screening use case."""
    return DeleteScreeningUseCase(screening_repository=screening_repository)


@pytest.mark.asyncio
async def test_deletes_and_returns_id(
    use_case: DeleteScreeningUseCase,
    screening_repository: ScreeningRepository,
) -> None:
    """A successful hard delete returns the deleted screening ID."""
    screening_repository.delete.return_value = True

    result = await use_case.execute(
        DeleteScreeningUseCase.InputData(screening_id="scr-1")
    )

    assert result.screening_id == "scr-1"
    screening_repository.delete.assert_awaited_once_with(
        screening_id=ScreeningId(value="scr-1")
    )


@pytest.mark.asyncio
async def test_raises_when_screening_missing(
    use_case: DeleteScreeningUseCase,
    screening_repository: ScreeningRepository,
) -> None:
    """Deleting an unknown screening raises ScreeningNotFoundError."""
    screening_repository.delete.return_value = False

    with pytest.raises(ScreeningNotFoundError, match="scr-missing"):
        await use_case.execute(
            DeleteScreeningUseCase.InputData(screening_id="scr-missing")
        )

    screening_repository.delete.assert_awaited_once_with(
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
