"""Tests for ListCinemaSourceAssignmentsUseCase."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import CinemaSourceAssignmentRepository
from marquise.application.use_cases import ListCinemaSourceAssignmentsUseCase
from marquise.domain.entities import Cinema, CinemaSourceAssignment, SourceDefinition
from marquise.domain.value_objects import CinemaId, SourceName


@pytest.mark.asyncio
async def test_list_cinema_source_assignments_returns_all_assignments() -> None:
    """Verify every assignment maps to its cinema ID and source label."""
    repository = create_autospec(CinemaSourceAssignmentRepository, instance=True)
    repository.find_all.return_value = [
        CinemaSourceAssignment(
            cinema=Cinema(id=CinemaId(value="cin-001"), name="Cinema One"),
            source=SourceDefinition(
                name=SourceName(value="cineplex"), display_name="Cineplex"
            ),
        )
    ]
    use_case = ListCinemaSourceAssignmentsUseCase(repository)

    response = await use_case.execute(ListCinemaSourceAssignmentsUseCase.InputData())

    assert response.assignments == [
        ListCinemaSourceAssignmentsUseCase.AssignmentData(
            cinema_id="cin-001", source_display_name="Cineplex"
        )
    ]
    repository.find_all.assert_awaited_once()
