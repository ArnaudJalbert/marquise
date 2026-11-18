"""List one movie's screening summaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.readers import ScreeningReader
from marquise.application.repositories import MovieRepository
from marquise.application.repositories.page import get_page_offset
from marquise.domain.value_objects import MovieId


class GetMovieScreeningsQuery:
    """Query screening summaries for one movie."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for movie screening summaries."""

        movie_id: str
        page: int
        size: int
        start: datetime | None = None

        def __post_init__(self) -> None:
            """Validate movie ID and pagination."""
            if not self.movie_id.strip():
                raise ValueError("movie_id must not be empty")
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
        movie_repository: MovieRepository,
        screening_reader: ScreeningReader,
    ) -> None:
        """Initialize query collaborators."""
        self.movie_repository = movie_repository
        self.screening_reader = screening_reader

    async def execute(self, input_data: InputData) -> OutputData:
        """Return paginated screening summaries for one movie."""
        if not await self.movie_repository.exists_by_id(
            MovieId(value=input_data.movie_id)
        ):
            raise MovieNotFoundError(
                f"A movie with ID '{input_data.movie_id}' was not found"
            )
        start_filter = (
            {"start_date": input_data.start} if input_data.start is not None else {}
        )
        page = await self.screening_reader.search(
            movie_id=input_data.movie_id,
            **start_filter,
            limit=input_data.size,
            offset=get_page_offset(input_data.page, input_data.size),
        )
        return self.OutputData(screenings=tuple(page.items), total=page.total)
