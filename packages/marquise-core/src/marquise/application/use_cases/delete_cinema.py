"""Delete cinema use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.repositories import CinemaRepository
from marquise.domain.value_objects import CinemaId


class DeleteCinemaUseCase:
    """Use case for deleting a cinema by its ID.

    Attempts to delete the cinema and raises an error if no cinema
    with the given ID exists.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for deleting a cinema.

        Attributes:
            cinema_id: The unique identifier of the cinema to delete.
        """

        cinema_id: str

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If the cinema_id is empty or whitespace-only.
            """
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after successful cinema deletion.

        Attributes:
            cinema_id: The ID of the deleted cinema.
        """

        cinema_id: str

    def __init__(self, cinema_repository: CinemaRepository) -> None:
        """Initialize the use case.

        Args:
            cinema_repository: A repository for cinema persistence.
        """
        self.cinema_repository = cinema_repository

    async def execute(self, input_data: InputData) -> OutputData:
        """Delete a cinema by its ID.

        Args:
            input_data: The input data containing the cinema ID.

        Returns:
            The output data containing the deleted cinema's ID.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        cinema_id = CinemaId(value=input_data.cinema_id)
        deleted = await self.cinema_repository.delete(cinema_id)

        if not deleted:
            raise CinemaNotFoundError(
                f"A cinema with ID '{input_data.cinema_id}' was not found"
            )

        return self.OutputData(cinema_id=input_data.cinema_id)
