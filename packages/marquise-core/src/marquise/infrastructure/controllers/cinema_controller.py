"""Controller for cinema management operations."""

from __future__ import annotations

from datetime import datetime

from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_screenings import (
    GetCinemaScreeningsUseCase,
)
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase


class CinemaController:
    """Handles cinema creation, listing, and deletion flows.

    All dependencies are injected — no settings, database, or use case wiring
    lives here.  The caller is responsible for initializing and shutting down
    the database.
    """

    def __init__(
        self,
        create_cinema_use_case: CreateCinemaUseCase,
        delete_cinema_use_case: DeleteCinemaUseCase,
        get_cinema_use_case: GetCinemaUseCase,
        get_cinema_movies_use_case: GetCinemaMoviesUseCase,
        get_cinema_screenings_use_case: GetCinemaScreeningsUseCase,
        list_cinemas_use_case: ListCinemasUseCase,
        update_cinema_use_case: UpdateCinemaUseCase,
    ) -> None:
        self._create_use_case = create_cinema_use_case
        self._delete_use_case = delete_cinema_use_case
        self._get_use_case = get_cinema_use_case
        self._get_movies_use_case = get_cinema_movies_use_case
        self._get_screenings_use_case = get_cinema_screenings_use_case
        self._list_use_case = list_cinemas_use_case
        self._update_use_case = update_cinema_use_case

    async def create(
        self,
        name: str,
        address: str | None = None,
        city: str | None = None,
        website: str | None = None,
    ) -> CreateCinemaUseCase.OutputData:
        """Create a new cinema.

        Delegates to the create-cinema use case.

        Args:
            name: Cinema name.
            address: Street address (optional).
            city: City (optional).
            website: Website URL (optional).

        Returns:
            The output data from the use case.

        Raises:
            CinemaAlreadyExistsError: If a cinema with the same name+address
                exists.
            CinemaIdAlreadyExistsError: On UUID collision.
        """
        request = CreateCinemaUseCase.InputData(
            name=name,
            address=address,
            city=city,
            website=website,
        )
        return await self._create_use_case.execute(request)

    async def list_cinemas(
        self,
        name_filter: str | None = None,
    ) -> ListCinemasUseCase.OutputData:
        """List cinemas with optional name filter.

        Delegates to the list-cinemas use case.

        Args:
            name_filter: Optional name substring filter (case-insensitive).

        Returns:
            The output data from the use case.
        """
        request = ListCinemasUseCase.InputData(name=name_filter)
        return await self._list_use_case.execute(request)

    async def delete(self, cinema_id: str) -> DeleteCinemaUseCase.OutputData:
        """Delete a cinema by its ID.

        Delegates to the delete-cinema use case.

        Args:
            cinema_id: The ID of the cinema to delete.

        Returns:
            The output data from the use case.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        request = DeleteCinemaUseCase.InputData(cinema_id=cinema_id)
        return await self._delete_use_case.execute(request)

    async def update(
        self,
        cinema_id: str,
        name: str,
        address: str | None = None,
        city: str | None = None,
        website: str | None = None,
    ) -> UpdateCinemaUseCase.OutputData:
        """Update an existing cinema.

        Delegates to the update-cinema use case.

        Args:
            cinema_id: The ID of the cinema to update.
            name: New cinema name.
            address: New street address (optional).
            city: New city (optional).
            website: New website URL (optional).

        Returns:
            The output data from the use case.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        request = UpdateCinemaUseCase.InputData(
            cinema_id=cinema_id,
            name=name,
            address=address,
            city=city,
            website=website,
        )
        return await self._update_use_case.execute(request)

    async def list(
        self,
        name: str | None = None,
        page: int = 1,
        size: int | None = None,
    ) -> ListCinemasUseCase.OutputData:
        """List cinemas, optionally filtered by name and paginated.

        This is a public operation — no authentication required.

        Args:
            name: Optional name filter (case-insensitive substring).
            page: Page number (1-based). Ignored when size is None.
            size: Max number of items per page. If None, all matching
                cinemas are returned unbounded (page is ignored).

        Returns:
            The output data containing the matching page of cinemas and the
            total count.
        """
        request = ListCinemasUseCase.InputData(name=name, page=page, size=size)
        return await self._list_use_case.execute(request)

    async def get(self, cinema_id: str) -> GetCinemaUseCase.OutputData:
        """Retrieve a single cinema by its ID.

        This is a public operation — no authentication required.

        Args:
            cinema_id: The ID of the cinema to retrieve.

        Returns:
            The output data describing the cinema.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        request = GetCinemaUseCase.InputData(cinema_id=cinema_id)
        return await self._get_use_case.execute(request)

    async def get_screenings(
        self,
        cinema_id: str,
        page: int = 1,
        size: int | None = None,
    ) -> GetCinemaScreeningsUseCase.OutputData:
        """List all of a cinema's screenings.

        This is a public operation — no authentication required.

        Args:
            cinema_id: The cinema to fetch screenings for.
            page: Page number (1-based). Ignored when size is None.
            size: Max number of screenings per page. If None, all matching
                screenings are returned unbounded (page is ignored).

        Returns:
            The output data with the cinema, its page of screenings, and the
            total count.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        request = GetCinemaScreeningsUseCase.InputData(
            cinema_id=cinema_id, page=page, size=size
        )
        return await self._get_screenings_use_case.execute(request)

    async def get_movies(
        self,
        cinema_id: str,
        start_date: datetime,
        end_date: datetime,
        page: int = 1,
        size: int | None = None,
    ) -> GetCinemaMoviesUseCase.OutputData:
        """List the distinct movies currently screening at a cinema.

        This is a public operation — no authentication required.

        Args:
            cinema_id: The cinema to fetch movies for.
            start_date: Start of the range (inclusive).
            end_date: End of the range (inclusive).
            page: Page number (1-based). Ignored when size is None.
            size: Max number of movies per page. If None, all matching
                movies are returned unbounded (page is ignored).

        Returns:
            The output data with the cinema, its page of distinct movies, and
            the total count.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        request = GetCinemaMoviesUseCase.InputData(
            cinema_id=cinema_id,
            start_date=start_date,
            end_date=end_date,
            page=page,
            size=size,
        )
        return await self._get_movies_use_case.execute(request)
