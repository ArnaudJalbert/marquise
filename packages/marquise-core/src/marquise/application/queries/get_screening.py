"""Get screening by ID query."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.readers import ScreeningReader


class GetScreeningQuery:
    """Query for retrieving one screening projection by ID."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for fetching a screening.

        Attributes:
            screening_id: Unique identifier of the screening.
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
        """Retrieved screening projection."""

        id: str
        movie_id: str
        movie_title: str
        cinema_id: str
        cinema_name: str
        showtime: datetime
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

    def __init__(self, screening_reader: ScreeningReader) -> None:
        """Initialize with screening reader."""
        self.screening_reader = screening_reader

    async def execute(self, request: InputData) -> OutputData:
        """Retrieve one screening projection.

        Args:
            request: Screening lookup input.

        Returns:
            Matching screening output data.

        Raises:
            ScreeningNotFoundError: If screening does not exist.
        """
        screening = await self.screening_reader.get_by_id(request.screening_id)
        if screening is None:
            raise ScreeningNotFoundError(
                f"A screening with ID '{request.screening_id}' was not found"
            )
        return self.OutputData(
            id=screening.id,
            movie_id=screening.movie_id,
            movie_title=screening.movie_title,
            cinema_id=screening.cinema_id,
            cinema_name=screening.cinema_name,
            showtime=screening.showtime,
            ticket_url=screening.ticket_url,
            room=screening.room,
            language=screening.language,
        )
