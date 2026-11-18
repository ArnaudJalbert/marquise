"""List one cinema's screening summaries."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.readers import ScreeningReader
from marquise.application.repositories import CinemaRepository
from marquise.application.repositories.page import get_page_offset
from marquise.domain.value_objects import CinemaId


class GetCinemaScreeningsQuery:
    """Query screening summaries for one cinema."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for cinema screening summaries."""

        cinema_id: str
        page: int
        size: int

        def __post_init__(self) -> None:
            """Validate cinema ID and pagination."""
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if self.size < 1:
                raise ValueError("size must be positive")
            if self.page < 1:
                raise ValueError("page must be at least 1")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Screening summaries and matching total."""

        screenings: tuple[ScreeningReader.ScreeningData, ...]
        total: int

    def __init__(
        self,
        cinema_repository: CinemaRepository,
        screening_reader: ScreeningReader,
    ) -> None:
        """Initialize query collaborators."""
        self.cinema_repository = cinema_repository
        self.screening_reader = screening_reader

    async def execute(self, input_data: InputData) -> OutputData:
        """Return paginated screening summaries for one cinema."""
        if not await self.cinema_repository.exists_by_id(
            CinemaId(value=input_data.cinema_id)
        ):
            raise CinemaNotFoundError(
                f"A cinema with ID '{input_data.cinema_id}' was not found"
            )
        page = await self.screening_reader.search(
            cinema_id=input_data.cinema_id,
            limit=input_data.size,
            offset=get_page_offset(input_data.page, input_data.size),
        )
        return self.OutputData(screenings=tuple(page.items), total=page.total)
