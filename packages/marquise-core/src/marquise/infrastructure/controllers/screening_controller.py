"""Controller for screening read operations."""

from __future__ import annotations

from datetime import datetime

from marquise.application.use_cases.get_screening import GetScreeningUseCase
from marquise.application.use_cases.search_screenings import SearchScreeningsUseCase


class ScreeningController:
    """Handles screening read flows.

    All methods are public — no authentication required.  Use case instances
    are injected at construction time.
    """

    def __init__(
        self,
        get_screening_use_case: GetScreeningUseCase,
        search_screenings_use_case: SearchScreeningsUseCase,
    ) -> None:
        self._get_use_case = get_screening_use_case
        self._search_use_case = search_screenings_use_case

    async def get(self, screening_id: str) -> GetScreeningUseCase.OutputData:
        """Retrieve a single screening by its ID.

        This is a public operation — no authentication required.

        Args:
            screening_id: The ID of the screening to retrieve.

        Returns:
            The output data describing the screening.

        Raises:
            ScreeningNotFoundError: If no screening with the given ID exists.
        """
        request = GetScreeningUseCase.InputData(screening_id=screening_id)
        return await self._get_use_case.execute(request)

    async def search(
        self,
        movie: str | None = None,
        movie_id: str | None = None,
        cinema_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        language: str | None = None,
        page: int = 1,
        size: int | None = None,
    ) -> SearchScreeningsUseCase.OutputData:
        """Search screenings across all cinemas by any combination of filters.

        This is a public operation — no authentication required.

        Args:
            movie: Optional movie title substring filter (case-insensitive).
            movie_id: Optional exact movie ID filter.
            cinema_id: Optional exact cinema ID filter.
            start_date: Optional start of the showtime range (inclusive).
            end_date: Optional end of the showtime range (inclusive).
            language: Optional exact language/subtitle version filter.
            page: Page number (1-based). Ignored when size is None.
            size: Max number of screenings per page. If None, all matching
                screenings are returned unbounded (page is ignored).

        Returns:
            The output data with the matching page of screenings and the
            total count.
        """
        request = SearchScreeningsUseCase.InputData(
            movie=movie,
            movie_id=movie_id,
            cinema_id=cinema_id,
            start_date=start_date,
            end_date=end_date,
            language=language,
            page=page,
            size=size,
        )
        return await self._search_use_case.execute(request)
