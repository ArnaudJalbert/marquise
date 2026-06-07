"""Get cinema source use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import CinemaSourceAssignmentNotFoundError
from marquise.application.repositories import (
    CinemaSourceAssignmentRepository,
    SourceDefinitionRepository,
)
from marquise.domain.value_objects import CinemaId, SourceName


class GetCinemaSourceUseCase:
    """Use case for retrieving the source assigned to a cinema."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for retrieving a cinema's source.

        Attributes:
            cinema_id: The ID of the cinema to look up.
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
        """Output data containing the assigned source information.

        Attributes:
            cinema_id: The ID of the cinema.
            source_name: The machine name of the assigned source.
            source_display_name: The human-readable label of the source.
        """

        cinema_id: str
        source_name: str
        source_display_name: str

        def __post_init__(self) -> None:
            """Validate output data.

            Raises:
                ValueError: If any field is empty or whitespace-only.
            """
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if not self.source_name.strip():
                raise ValueError("source_name must not be empty")
            if not self.source_display_name.strip():
                raise ValueError("source_display_name must not be empty")

    def __init__(
        self,
        assignment_repository: CinemaSourceAssignmentRepository,
        source_definition_repository: SourceDefinitionRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            assignment_repository: Repository for assignment lookups.
            source_definition_repository: Repository for source definition lookups.
        """
        self.assignment_repository = assignment_repository
        self.source_definition_repository = source_definition_repository

    async def execute(self, request: InputData) -> OutputData:
        """Retrieve the source assigned to a cinema.

        Args:
            request: The input data containing the cinema ID.

        Returns:
            The output data with the assigned source details.

        Raises:
            CinemaSourceAssignmentNotFoundError: If no assignment exists
                for the given cinema.
        """
        cinema_id = CinemaId(value=request.cinema_id)

        assignment = await self.assignment_repository.find_by_cinema_id(cinema_id)
        if assignment is None:
            raise CinemaSourceAssignmentNotFoundError(
                f"No source assignment found for cinema '{request.cinema_id}'"
            )

        source = await self.source_definition_repository.find_by_name(
            SourceName(value=str(assignment.source_name))
        )

        source_display_name = (
            source.display_name if source is not None else str(assignment.source_name)
        )

        return self.OutputData(
            cinema_id=request.cinema_id,
            source_name=str(assignment.source_name),
            source_display_name=source_display_name,
        )
