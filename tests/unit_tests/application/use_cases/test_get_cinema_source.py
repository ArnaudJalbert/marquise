"""Tests for GetCinemaSourceUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import CinemaSourceAssignmentNotFoundError
from marquise.application.repositories import (
    CinemaSourceAssignmentRepository,
    SourceDefinitionRepository,
)
from marquise.application.use_cases import GetCinemaSourceUseCase
from marquise.domain.entities import CinemaSourceAssignment, SourceDefinition
from marquise.domain.value_objects import CinemaId, SourceName


@pytest.mark.asyncio
async def test_get_cinema_source_returns_assignment() -> None:
    """Verify the happy path: assignment is found and returned."""
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_source_repo = create_autospec(SourceDefinitionRepository, instance=True)

    mock_assignment_repo.find_by_cinema_id.return_value = CinemaSourceAssignment(
        cinema_id=CinemaId(value="cin-001"),
        source_name=SourceName(value="cineplex"),
    )
    mock_source_repo.find_by_name.return_value = SourceDefinition(
        name=SourceName(value="cineplex"),
        display_name="Cineplex",
    )

    use_case = GetCinemaSourceUseCase(
        assignment_repository=mock_assignment_repo,
        source_definition_repository=mock_source_repo,
    )
    request = GetCinemaSourceUseCase.InputData(cinema_id="cin-001")

    response = await use_case.execute(request)

    assert response.cinema_id == "cin-001"
    assert response.source_name == "cineplex"
    assert response.source_display_name == "Cineplex"
    mock_assignment_repo.find_by_cinema_id.assert_awaited_once()
    mock_source_repo.find_by_name.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_cinema_source_raises_not_found() -> None:
    """Verify raises when no assignment exists."""
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_source_repo = create_autospec(SourceDefinitionRepository, instance=True)

    mock_assignment_repo.find_by_cinema_id.return_value = None

    use_case = GetCinemaSourceUseCase(
        assignment_repository=mock_assignment_repo,
        source_definition_repository=mock_source_repo,
    )
    request = GetCinemaSourceUseCase.InputData(cinema_id="cin-001")

    with pytest.raises(
        CinemaSourceAssignmentNotFoundError, match="No source assignment found"
    ):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_get_cinema_source_falls_back_when_source_definition_missing() -> None:
    """Verify display_name falls back to source_name when definition is gone."""
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )
    mock_source_repo = create_autospec(SourceDefinitionRepository, instance=True)

    mock_assignment_repo.find_by_cinema_id.return_value = CinemaSourceAssignment(
        cinema_id=CinemaId(value="cin-001"),
        source_name=SourceName(value="orphaned"),
    )
    mock_source_repo.find_by_name.return_value = None

    use_case = GetCinemaSourceUseCase(
        assignment_repository=mock_assignment_repo,
        source_definition_repository=mock_source_repo,
    )
    request = GetCinemaSourceUseCase.InputData(cinema_id="cin-001")

    response = await use_case.execute(request)

    assert response.cinema_id == "cin-001"
    assert response.source_name == "orphaned"
    assert response.source_display_name == "orphaned"
