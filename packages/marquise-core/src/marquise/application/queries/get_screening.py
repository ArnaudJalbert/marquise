"""Query one screening's display data without constructing domain entities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.readers import ScreeningReader


class GetScreeningQuery:
    """Retrieve one screening projection through an injected reader."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """The exact ID of the screening to retrieve."""

        screening_id: str

        def __post_init__(self) -> None:
            """Reject empty or whitespace-only screening identifiers."""
            if not self.screening_id.strip():
                raise ValueError("screening_id must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Display data for the retrieved screening."""

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
        """Initialize with a reader for screening display data."""
        self.screening_reader = screening_reader

    async def execute(self, input_data: InputData) -> OutputData:
        """Return the projection for the requested screening ID.

        Raises:
            ScreeningNotFoundError: If no screening with this exact ID exists.
        """
        screening = await self.screening_reader.find_by_id(input_data.screening_id)
        if screening is None:
            raise ScreeningNotFoundError(
                f"A screening with ID '{input_data.screening_id}' was not found"
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
