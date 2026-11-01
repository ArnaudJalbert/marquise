"""Delete screening use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.repositories import ScreeningRepository
from marquise.application.use_cases._screening_helpers import require_non_empty
from marquise.domain.value_objects import ScreeningId


class DeleteScreeningUseCase:
    """Use case for permanently deleting a screening by its ID."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for deleting a screening.

        Attributes:
            screening_id: The unique identifier of the screening to delete.
        """

        screening_id: str

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If screening_id is empty or whitespace-only.
            """
            require_non_empty(self.screening_id, "screening_id")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after successful screening deletion."""

        screening_id: str

    def __init__(self, screening_repository: ScreeningRepository) -> None:
        """Initialize the use case.

        Args:
            screening_repository: Repository for screening persistence.
        """
        self.screening_repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        """Permanently delete a screening by its ID.

        Args:
            request: The input data containing the screening ID.

        Returns:
            The output data containing the deleted screening ID.

        Raises:
            ScreeningNotFoundError: If no screening with the given ID exists.
        """
        deleted = await self.screening_repository.delete(
            screening_id=ScreeningId(value=request.screening_id)
        )
        if not deleted:
            raise ScreeningNotFoundError(
                f"A screening with ID '{request.screening_id}' was not found"
            )
        return self.OutputData(screening_id=request.screening_id)
