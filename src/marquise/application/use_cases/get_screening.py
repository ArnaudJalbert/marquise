"""Get screening by ID use case (read-only)."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.repositories import ScreeningRepository
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
            if not self.screening_id.strip():
                raise ValueError("screening_id must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """The retrieved screening's output data.

        Attributes:
            id: Unique identifier of the screening.
            movie_id: The screened movie's ID.
            movie_title: The screened movie's title.
            showtime: The screening time in ISO 8601 format.
            ticket_url: Link to purchase tickets (optional).
            room: Room or auditorium name (optional).
            language: Language or subtitle version (optional).
        """

        id: str
        movie_id: str
        movie_title: str
        showtime: str
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

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
        if screening is None:
            raise ScreeningNotFoundError(
                f"A screening with ID '{request.screening_id}' was not found"
            )

        return self.OutputData(
            id=str(screening.id),
            movie_id=str(screening.movie.id),
            movie_title=screening.movie.title,
            showtime=screening.showtime.value.isoformat(),
            ticket_url=screening.ticket_url,
            room=screening.room,
            language=screening.language,
        )
