"""List cinema-source assignments use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.repositories import CinemaSourceAssignmentRepository


class ListCinemaSourceAssignmentsUseCase:
    """Use case for listing every cinema-source assignment."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing assignments (no parameters)."""

    @dataclass(frozen=True, slots=True)
    class AssignmentData:
        """An assigned source for one cinema."""

        cinema_id: str
        source_display_name: str

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing cinema-source assignments."""

        assignments: list[ListCinemaSourceAssignmentsUseCase.AssignmentData]

    def __init__(self, assignment_repository: CinemaSourceAssignmentRepository) -> None:
        """Initialize with cinema-source assignment repository."""
        self.assignment_repository = assignment_repository

    async def execute(self, request: InputData) -> OutputData:
        """List cinema-source assignments."""
        assignments = await self.assignment_repository.find_all()
        return self.OutputData(
            assignments=[
                self.AssignmentData(
                    cinema_id=str(assignment.cinema.id),
                    source_display_name=assignment.source.display_name,
                )
                for assignment in assignments
            ]
        )
