"""Unassign source from cinema use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import CinemaSourceAssignmentNotFoundError
from marquise.application.repositories import CinemaSourceAssignmentRepository
from marquise.domain.value_objects import CinemaId


class UnassignSourceUseCase:
    """Use case for removing a source assignment from a cinema."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for unassigning a source from a cinema.

        Attributes:
            cinema_id: The ID of the cinema to remove the assignment from.
        """

        cinema_id: str

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If ``cinema_id`` is empty or whitespace-only.
            """
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after successful unassignment.

        Attributes:
            cinema_id: The ID of the cinema that was unassigned.
        """

        cinema_id: str

    def __init__(self, assignment_repository: CinemaSourceAssignmentRepository) -> None:
        """Initialize the use case.

        Args:
            assignment_repository: Repository for assignment persistence.
        """
        self.assignment_repository = assignment_repository

    async def execute(self, request: InputData) -> OutputData:
        """Unassign the source from a cinema.

        Args:
            request: The input data containing the cinema ID.

        Returns:
            The output data confirming the unassignment.

        Raises:
            CinemaSourceAssignmentNotFoundError: If no assignment exists
                for the given cinema.
        """
        cinema_id = CinemaId(value=request.cinema_id)
        removed = await self.assignment_repository.unassign(cinema_id)

        if not removed:
            raise CinemaSourceAssignmentNotFoundError(
                f"No source assignment found for cinema '{request.cinema_id}'"
            )

        return self.OutputData(cinema_id=request.cinema_id)
