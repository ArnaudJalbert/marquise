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
    """Provide autospecced screening repository."""
    return create_autospec(ScreeningRepository, instance=True)


@pytest.fixture
def use_case(
    screening_repository: ScreeningRepository,
) -> DeleteScreeningUseCase:
    """Provide configured delete-screening use case."""
    return DeleteScreeningUseCase(screening_repository=screening_repository)


@pytest.mark.asyncio
async def test_deletes_screening(
    use_case: DeleteScreeningUseCase,
    screening_repository: ScreeningRepository,
) -> None:
    """Successful delete removes only the requested screening."""
    result = await use_case.execute(
        DeleteScreeningUseCase.InputData(screening_id="scr-1")
    )

    assert result.screening_id == "scr-1"
    screening_repository.delete.assert_awaited_once_with(
        screening_id=ScreeningId(value="scr-1")
    )


@pytest.mark.asyncio
async def test_missing_screening_error_propagates(
    use_case: DeleteScreeningUseCase,
    screening_repository: ScreeningRepository,
) -> None:
    """Missing screening errors propagate from delete."""
    screening_repository.delete.side_effect = ScreeningNotFoundError(
        "A screening with ID 'scr-missing' was not found"
    )

    with pytest.raises(ScreeningNotFoundError, match="scr-missing"):
        await use_case.execute(
            DeleteScreeningUseCase.InputData(screening_id="scr-missing")
        )

    screening_repository.delete.assert_awaited_once_with(
        screening_id=ScreeningId(value="scr-missing")
    )


def test_input_rejects_empty_screening_id() -> None:
    """Empty screening_id is rejected."""
    with pytest.raises(ValueError, match="screening_id must not be empty"):
        DeleteScreeningUseCase.InputData(screening_id="  ")
