"""Get screening by ID use case (read-only)."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.repositories import ScreeningRepository
from marquise.application.use_cases._screening_helpers import (
    ScreeningDetailOutput,
    require_non_empty,
    screening_output_data,
)
from marquise.domain.value_objects import ScreeningId


class GetScreeningUseCase:
    """Use case for retrieving a single screening by its ID."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for fetching a screening.

        Attributes:
            screening_id: The unique identifier of the screening.
        """

        screening_id: str

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If screening_id is empty or whitespace-only.
            """
            require_non_empty(self.screening_id, "screening_id")

    OutputData = ScreeningDetailOutput

    def __init__(self, screening_repository: ScreeningRepository) -> None:
        """Initialize the use case.

        Args:
            screening_repository: A repository for querying screenings.
        """
        self.screening_repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        """Retrieve a screening by its ID.

        Args:
            request: The input data containing the screening ID.

        Returns:
            The output data describing the screening.

        Raises:
            ScreeningNotFoundError: If no screening with the given ID exists.
        """
        screening = await self.screening_repository.find_by_id(
            ScreeningId(value=request.screening_id)
        )

        return screening_output_data(screening)
