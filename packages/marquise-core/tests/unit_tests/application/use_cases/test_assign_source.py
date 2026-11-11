"""Tests for AssignSourceUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    CinemaNotFoundError,
    CinemaSourceAssignmentAlreadyExistsError,
    SourceNotFoundError,
)
from marquise.application.repositories import (
    CinemaRepository,
    CinemaSourceAssignmentRepository,
    SourceDefinitionRepository,
)
from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.domain.entities import Cinema, CinemaSourceAssignment, SourceDefinition
from marquise.domain.value_objects import CinemaId, SourceName


@pytest.mark.asyncio
async def test_assign_source_saves_and_returns_response() -> None:
    """Verify the happy path: assignment is saved and response is correct."""
    cinema = Cinema(id=CinemaId(value="cin-001"), name="Test Cinema")
    source = SourceDefinition(
        name=SourceName(value="cineplex"), display_name="Cineplex"
    )
    saved = CinemaSourceAssignment(cinema=cinema, source=source)

    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_source_repo = create_autospec(SourceDefinitionRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )

    mock_cinema_repo.find_by_id.return_value = cinema
    mock_source_repo.find_by_name.return_value = source
    mock_assignment_repo.find_by_cinema_id.return_value = None
    mock_assignment_repo.assign.return_value = saved

    use_case = AssignSourceUseCase(
        cinema_repository=mock_cinema_repo,
        source_definition_repository=mock_source_repo,
        assignment_repository=mock_assignment_repo,
    )
    request = AssignSourceUseCase.InputData(cinema_id="cin-001", source_name="cineplex")

    response = await use_case.execute(request)

    assert response.cinema_id == "cin-001"
    assert response.source_name == "cineplex"
    mock_cinema_repo.find_by_id.assert_awaited_once()
    mock_source_repo.find_by_name.assert_awaited_once()
    mock_assignment_repo.find_by_cinema_id.assert_awaited_once()
    mock_assignment_repo.assign.assert_awaited_once()


@pytest.mark.asyncio
async def test_assign_source_raises_when_cinema_not_found() -> None:
    """Verify CinemaNotFoundError is raised when cinema doesn't exist."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_source_repo = create_autospec(SourceDefinitionRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )

    mock_cinema_repo.find_by_id.return_value = None

    use_case = AssignSourceUseCase(
        cinema_repository=mock_cinema_repo,
        source_definition_repository=mock_source_repo,
        assignment_repository=mock_assignment_repo,
    )
    request = AssignSourceUseCase.InputData(
        cinema_id="cin-missing", source_name="cineplex"
    )

    with pytest.raises(CinemaNotFoundError, match="was not found"):
        await use_case.execute(request)

    mock_cinema_repo.find_by_id.assert_awaited_once()
    mock_assignment_repo.assign.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_source_raises_when_source_not_found() -> None:
    """Verify SourceNotFoundError is raised when source doesn't exist."""
    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_source_repo = create_autospec(SourceDefinitionRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )

    mock_cinema_repo.find_by_id.return_value = Cinema(
        id=CinemaId(value="cin-001"),
        name="Test Cinema",
    )
    mock_source_repo.find_by_name.return_value = None

    use_case = AssignSourceUseCase(
        cinema_repository=mock_cinema_repo,
        source_definition_repository=mock_source_repo,
        assignment_repository=mock_assignment_repo,
    )
    request = AssignSourceUseCase.InputData(cinema_id="cin-001", source_name="missing")

    with pytest.raises(SourceNotFoundError, match="was not found"):
        await use_case.execute(request)

    mock_assignment_repo.assign.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_source_raises_when_already_assigned() -> None:
    """Verify error when cinema already has a source assigned."""
    cinema = Cinema(id=CinemaId(value="cin-001"), name="Test Cinema")
    existing_source = SourceDefinition(
        name=SourceName(value="cinema_du_parc"), display_name="Cinema du Parc"
    )
    existing = CinemaSourceAssignment(cinema=cinema, source=existing_source)

    mock_cinema_repo = create_autospec(CinemaRepository, instance=True)
    mock_source_repo = create_autospec(SourceDefinitionRepository, instance=True)
    mock_assignment_repo = create_autospec(
        CinemaSourceAssignmentRepository, instance=True
    )

    mock_cinema_repo.find_by_id.return_value = cinema
    mock_source_repo.find_by_name.return_value = SourceDefinition(
        name=SourceName(value="cineplex"),
        display_name="Cineplex",
    )
    mock_assignment_repo.find_by_cinema_id.return_value = existing

    use_case = AssignSourceUseCase(
        cinema_repository=mock_cinema_repo,
        source_definition_repository=mock_source_repo,
        assignment_repository=mock_assignment_repo,
    )
    request = AssignSourceUseCase.InputData(cinema_id="cin-001", source_name="cineplex")

    with pytest.raises(
        CinemaSourceAssignmentAlreadyExistsError, match="already assigned"
    ):
        await use_case.execute(request)

    mock_assignment_repo.assign.assert_not_awaited()
