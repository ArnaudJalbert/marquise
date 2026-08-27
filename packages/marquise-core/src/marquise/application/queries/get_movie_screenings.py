"""List one movie's screening summaries."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.readers import ScreeningReader, ScreeningSummary
from marquise.application.repositories import MovieRepository
from marquise.domain.value_objects import MovieId


class GetMovieScreeningsQuery:
    """Query screening summaries for one movie."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for movie screening summaries."""

        movie_id: str
        page: int = 1
        size: int | None = None

        def __post_init__(self) -> None:
            """Validate movie ID and pagination."""
            if not self.movie_id.strip():
                raise ValueError("movie_id must not be empty")
            if self.size is not None and self.size < 1:
                raise ValueError("size must be positive when provided")
            if self.page < 1:
                raise ValueError("page must be at least 1")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Screening summaries and matching total."""

        screenings: tuple[ScreeningSummary, ...]
        total: int

    def __init__(
        self,
        movie_repository: MovieRepository,
        screening_reader: ScreeningReader,
    ) -> None:
        """Initialize query collaborators."""
        self.movie_repository = movie_repository
        self.screening_reader = screening_reader

    async def execute(self, request: InputData) -> OutputData:
        """Return paginated screening summaries for one movie."""
        if not await self.movie_repository.exists_by_id(
            MovieId(value=request.movie_id)
        ):
            raise MovieNotFoundError(
                f"A movie with ID '{request.movie_id}' was not found"
            )
        limit = request.size
        offset = (request.page - 1) * request.size if request.size is not None else 0
        page = await self.screening_reader.search(
            movie_id=request.movie_id,
            limit=limit,
            offset=offset,
        )
        return self.OutputData(screenings=tuple(page.items), total=page.total)
