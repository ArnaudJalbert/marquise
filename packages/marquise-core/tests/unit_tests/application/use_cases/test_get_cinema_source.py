"""Tests for GetCinemaSourceUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaSourceAssignmentNotFoundError
from marquise.application.repositories import (
    CinemaSourceAssignmentRepository,
)
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.domain.entities import Cinema, CinemaSourceAssignment, SourceDefinition
from marquise.domain.value_objects import CinemaId, SourceName


@pytest.mark.asyncio
async def test_get_cinema_source_returns_assignment() -> None:
    """Verify the happy path: assignment is found and returned."""
    source = SourceDefinition(
        name=SourceName(value="cineplex"), display_name="Cineplex"
    )
    cinema = Cinema(id=CinemaId(value="cin-001"), name="Test Cinema")
    assignment = CinemaSourceAssignment(cinema=cinema, source=source)

    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_assignment_repo.find_by_cinema_id.return_value = assignment

    use_case = GetCinemaSourceUseCase(
        assignment_repository=mock_assignment_repo,
    )
    request = GetCinemaSourceUseCase.InputData(cinema_id="cin-001")

    response = await use_case.execute(request)

    assert response.cinema_id == "cin-001"
    assert response.source_name == "cineplex"
    assert response.source_display_name == "Cineplex"
    mock_assignment_repo.find_by_cinema_id.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_cinema_source_raises_not_found() -> None:
    """Verify raises when no assignment exists."""
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_assignment_repo.find_by_cinema_id.return_value = None

    use_case = GetCinemaSourceUseCase(
        assignment_repository=mock_assignment_repo,
    )
    request = GetCinemaSourceUseCase.InputData(cinema_id="cin-001")

    with pytest.raises(
        CinemaSourceAssignmentNotFoundError, match="No source assignment found"
    ):
        await use_case.execute(request)
