"""Controller for cinema management operations."""

from __future__ import annotations

from typing import Optional

from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.infrastructure.controllers.auth_controller import AuthController


class CinemaController:
    """Handles cinema creation, listing, and deletion flows.

    All dependencies are injected — no settings, database, or use case wiring
    lives here.  The caller is responsible for initializing and shutting down
    the database.
    """

    def __init__(
        self,
        auth_controller: AuthController,
        create_cinema_use_case: CreateCinemaUseCase,
        delete_cinema_use_case: DeleteCinemaUseCase,
        list_cinemas_use_case: ListCinemasUseCase,
        update_cinema_use_case: UpdateCinemaUseCase,
    ) -> None:
        self._auth = auth_controller
        self._create_use_case = create_cinema_use_case
        self._delete_use_case = delete_cinema_use_case
        self._list_use_case = list_cinemas_use_case
        self._update_use_case = update_cinema_use_case

    async def create(
        self,
        name: str,
        address: Optional[str] = None,
        city: Optional[str] = None,
        website: Optional[str] = None,
    ) -> CreateCinemaUseCase.OutputData:
        """Create a new cinema.

        Validates the caller is an admin and delegates to the create-cinema
        use case.

        Args:
            name: Cinema name.
            address: Street address (optional).
            city: City (optional).
            website: Website URL (optional).

        Returns:
            The output data from the use case.

        Raises:
            ValueError: If the caller is not authenticated as admin.
            CinemaAlreadyExistsError: If a cinema with the same name+address
                exists.
            CinemaIdAlreadyExistsError: On UUID collision.
        """
        self._auth.validate_admin()

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

        Validates the caller is an admin and delegates to the list-cinemas
        use case.

        Args:
            name_filter: Optional name substring filter (case-insensitive).

        Returns:
            The output data from the use case.

        Raises:
            ValueError: If the caller is not authenticated as admin.
        """
        self._auth.validate_admin()

        request = ListCinemasUseCase.InputData(name=name_filter)
        return await self._list_use_case.execute(request)

    async def delete(self, cinema_id: str) -> DeleteCinemaUseCase.OutputData:
        """Delete a cinema by its ID.

        Validates the caller is an admin and delegates to the delete-cinema
        use case.

        Args:
            cinema_id: The ID of the cinema to delete.

        Returns:
            The output data from the use case.

        Raises:
            ValueError: If the caller is not authenticated as admin.
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        self._auth.validate_admin()

        request = DeleteCinemaUseCase.InputData(cinema_id=cinema_id)
        return await self._delete_use_case.execute(request)

    async def update(
        self,
        cinema_id: str,
        name: str,
        address: Optional[str] = None,
        city: Optional[str] = None,
        website: Optional[str] = None,
    ) -> UpdateCinemaUseCase.OutputData:
        """Update an existing cinema.

        Validates the caller is an admin and delegates to the update-cinema
        use case.

        Args:
            cinema_id: The ID of the cinema to update.
            name: New cinema name.
            address: New street address (optional).
            city: New city (optional).
            website: New website URL (optional).

        Returns:
            The output data from the use case.

        Raises:
            ValueError: If the caller is not authenticated as admin.
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        self._auth.validate_admin()

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
        name: Optional[str] = None,
    ) -> ListCinemasUseCase.OutputData:
        """List cinemas, optionally filtered by name.

        This is a public operation — no authentication required.

        Args:
            name: Optional name filter (case-insensitive substring).

        Returns:
            The output data containing matching cinemas.
        """
        request = ListCinemasUseCase.InputData(name=name)
        return await self._list_use_case.execute(request)
