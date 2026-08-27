"""Get all of a cinema's screenings use case (read-only)."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.repositories import (
    CinemaRepository,
    ScreeningRepository,
    ScreeningSummary,
)
from marquise.domain.value_objects import CinemaId


class GetCinemaScreeningsUseCase:
    """Use case for listing all of a cinema's screenings.

    No filtering beyond the cinema scope is supported here — use
    ``SearchScreeningsQuery`` (``GET /v1/screenings``) for date range,
    movie, or language filters.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for fetching a cinema's screenings.

        Attributes:
            cinema_id: The cinema to fetch screenings for.
            page: Page number (1-based). Ignored when size is None.
            size: Max number of screenings per page. If None, all matching
                screenings are returned unbounded (page is ignored).
        """

        cinema_id: str
        page: int = 1
        size: int | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If cinema_id is empty, size is provided but not
                    positive, or page is less than 1.
            """
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if self.size is not None and self.size < 1:
                raise ValueError("size must be positive when provided")
            if self.page < 1:
                raise ValueError("page must be at least 1")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing the cinema's screenings.

        Attributes:
            cinema_id: The cinema's ID.
            cinema_name: The cinema's display name.
            screenings: The matching page of screenings, ordered by showtime.
            total: Total number of screenings for the cinema, ignoring
                limit/offset.
        """

        cinema_id: str
        cinema_name: str
        screenings: tuple[ScreeningSummary, ...]
        total: int

    def __init__(
        self,
        cinema_repository: CinemaRepository,
        screening_repository: ScreeningRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            cinema_repository: A repository for querying cinemas.
            screening_repository: A repository for querying screenings.
        """
        self.cinema_repository = cinema_repository
        self.screening_repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        """List all of a cinema's screenings.

        Args:
            request: The input data with cinema ID and pagination
                parameters.

        Returns:
            The output data with the cinema, its page of screenings, and the
            total count.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        cinema_id = CinemaId(value=request.cinema_id)
        if not await self.cinema_repository.exists_by_id(cinema_id):
            raise CinemaNotFoundError(
                f"A cinema with ID '{request.cinema_id}' was not found"
            )
        cinema = await self.cinema_repository.find_by_id(cinema_id)
        assert cinema is not None  # existence already verified above

        if request.size is not None:
            limit = request.size
            offset = (request.page - 1) * request.size
        else:
            limit = None
            offset = 0

        page = await self.screening_repository.search(
            cinema_id=cinema_id,
            limit=limit,
            offset=offset,
        )

        return self.OutputData(
            cinema_id=str(cinema.id),
            cinema_name=cinema.name,
            screenings=tuple(page.items),
            total=page.total,
        )
