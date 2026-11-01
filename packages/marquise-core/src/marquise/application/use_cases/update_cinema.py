"""Update cinema use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.repositories import CinemaRepository
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


class UpdateCinemaUseCase:
    """Use case for updating an existing cinema.

    Replaces all fields of an existing cinema identified by its ID and
    raises an error if no cinema with the given ID exists.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for updating a cinema.

        Attributes:
            cinema_id: Unique identifier of the cinema to update.
            name: New display name (required, non-empty).
            address: New street address (optional).
            city: New city (optional).
            website: New website URL (optional).
        """

        cinema_id: str
        name: str
        address: str | None = None
        city: str | None = None
        website: str | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If cinema_id or name is empty, or if
                    address/city/website are provided but whitespace-only.
            """
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if not self.name.strip():
                raise ValueError("name must not be empty")
            if self.address is not None and not self.address.strip():
                raise ValueError("address must not be empty when provided")
            if self.city is not None and not self.city.strip():
                raise ValueError("city must not be empty when provided")
            if self.website is not None and not self.website.strip():
                raise ValueError("website must not be empty when provided")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after a successful update.

        Attributes:
            id: The unique identifier of the updated cinema.
            name: Updated display name.
            address: Updated street address (optional).
            city: Updated city (optional).
            website: Updated website URL (optional).
        """

        id: str
        name: str
        address: str | None = None
        city: str | None = None
        website: str | None = None

    def __init__(self, cinema_repository: CinemaRepository) -> None:
        """Initialize the use case.

        Args:
            cinema_repository: A repository for cinema persistence.
        """
        self.cinema_repository = cinema_repository

    async def execute(self, request: InputData) -> OutputData:
        """Update an existing cinema.

        Constructs a cinema entity from the request and delegates to
        the repository.

        Args:
            request: The input data for updating the cinema.

        Returns:
            The output data containing the updated cinema details.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        cinema_id = CinemaId(value=request.cinema_id)
        cinema = Cinema(
            id=cinema_id,
            name=request.name,
            address=request.address,
            city=request.city,
            website=request.website,
        )
        updated = await self.cinema_repository.update(cinema)

        if updated is None:
            raise CinemaNotFoundError(
                f"A cinema with ID '{request.cinema_id}' was not found"
            )

        return self.OutputData(
            id=str(updated.id),
            name=updated.name,
            address=updated.address,
            city=updated.city,
            website=updated.website,
        )
