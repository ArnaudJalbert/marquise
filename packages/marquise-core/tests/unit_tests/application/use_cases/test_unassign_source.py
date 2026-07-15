"""Tests for UnassignSourceUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaSourceAssignmentNotFoundError
from marquise.application.repositories import CinemaSourceAssignmentRepository
from marquise.application.use_cases import UnassignSourceUseCase


@pytest.mark.asyncio
async def test_unassign_source_removes_and_returns_id() -> None:
    """Verify unassign removes the assignment and returns cinema_id."""
    mock_repo = create_autospec(CinemaSourceAssignmentRepository, instance=True)
    mock_repo.unassign.return_value = True

    use_case = UnassignSourceUseCase(assignment_repository=mock_repo)
    request = UnassignSourceUseCase.InputData(cinema_id="cin-001")

    response = await use_case.execute(request)

    assert response.cinema_id == "cin-001"
    mock_repo.unassign.assert_awaited_once()


@pytest.mark.asyncio
async def test_unassign_source_raises_not_found() -> None:
    """Verify unassign raises when no assignment exists."""
    mock_repo = create_autospec(CinemaSourceAssignmentRepository, instance=True)
    mock_repo.unassign.return_value = False

    use_case = UnassignSourceUseCase(assignment_repository=mock_repo)
    request = UnassignSourceUseCase.InputData(cinema_id="cin-001")

    with pytest.raises(
        CinemaSourceAssignmentNotFoundError, match="No source assignment found"
    ):
        await use_case.execute(request)

    mock_repo.unassign.assert_awaited_once()
