"""Assign source to cinema use case."""

from __future__ import annotations

from dataclasses import dataclass

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
from marquise.domain.entities import CinemaSourceAssignment
from marquise.domain.value_objects import CinemaId, SourceName


class AssignSourceUseCase:
    """Use case for assigning a showtime source to a cinema."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for assigning a source to a cinema.

        Attributes:
            cinema_id: The ID of the cinema to assign a source to.
            source_name: The name of the source to assign.
        """

        cinema_id: str
        source_name: str

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If ``cinema_id`` or ``source_name`` is empty.
            """
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if not self.source_name.strip():
                raise ValueError("source_name must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after successful source assignment.

        Attributes:
            cinema_id: The ID of the cinema.
            source_name: The name of the assigned source.
        """

        cinema_id: str
        source_name: str

        def __post_init__(self) -> None:
            """Validate output data.

            Raises:
                ValueError: If ``cinema_id`` or ``source_name`` is empty.
            """
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if not self.source_name.strip():
                raise ValueError("source_name must not be empty")

    def __init__(
        self,
        cinema_repository: CinemaRepository,
        source_definition_repository: SourceDefinitionRepository,
        assignment_repository: CinemaSourceAssignmentRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            cinema_repository: Repository for cinema lookups.
            source_definition_repository: Repository for source definition lookups.
            assignment_repository: Repository for assignment persistence.
        """
        self.cinema_repository = cinema_repository
        self.source_definition_repository = source_definition_repository
        self.assignment_repository = assignment_repository

    async def execute(self, request: InputData) -> OutputData:
        """Assign a source to a cinema.

        Validates that both the cinema and source exist, and that
        no existing assignment conflicts.

        Args:
            request: The input data containing cinema_id and source_name.

        Returns:
            The output data confirming the assignment.

        Raises:
            CinemaNotFoundError: If the cinema does not exist.
            SourceNotFoundError: If the source does not exist.
            CinemaSourceAssignmentAlreadyExistsError: If the cinema
                already has a source assigned.
        """
        cinema_id = CinemaId(value=request.cinema_id)
        source_name = SourceName(value=request.source_name)

        cinema = await self.cinema_repository.find_by_id(cinema_id)
        if cinema is None:
            raise CinemaNotFoundError(
                f"A cinema with ID '{request.cinema_id}' was not found"
            )

        source = await self.source_definition_repository.find_by_name(source_name)
        if source is None:
            raise SourceNotFoundError(
                f"A source with name '{request.source_name}' was not found"
            )

        existing = await self.assignment_repository.find_by_cinema_id(cinema_id)
        if existing is not None:
            raise CinemaSourceAssignmentAlreadyExistsError(
                f"Source '{existing.source_name}' is already assigned to"
                f" cinema '{request.cinema_id}'"
            )

        assignment = CinemaSourceAssignment(
            cinema_id=cinema_id,
            source_name=source_name,
        )

        saved = await self.assignment_repository.assign(assignment)

        return self.OutputData(
            cinema_id=str(saved.cinema_id),
            source_name=str(saved.source_name),
        )
