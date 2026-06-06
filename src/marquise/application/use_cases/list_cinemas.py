"""List cinemas use case."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from marquise.application.repositories import CinemaRepository


class ListCinemasUseCase:
    """Use case for listing cinemas with optional name filtering."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing cinemas.

        Attributes:
            name: Optional name filter (substring, case-insensitive).
        """

        name: Optional[str] = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If name is provided but empty or whitespace-only.
            """
            if self.name is not None and not self.name.strip():
                raise ValueError("name must not be empty when provided")

    @dataclass(frozen=True, slots=True)
    class CinemaData:
        """A single cinema's output data.

        Attributes:
            id: Unique identifier of the cinema.
            name: Display name of the cinema.
            address: Street address of the cinema (optional).
            city: City where the cinema is located (optional).
            website: Cinema's website URL (optional).
        """

        id: str
        name: str
        address: Optional[str] = None
        city: Optional[str] = None
        website: Optional[str] = None

        def __post_init__(self) -> None:
            """Validate cinema data.

            Raises:
                ValueError: If id or name is empty, or if optional fields
                    are provided but whitespace-only.
            """
            if not self.id.strip():
                raise ValueError("id must not be empty")
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
        """Output data containing the list of cinemas.

        Attributes:
            cinemas: The list of matching cinemas.
        """

        cinemas: list[ListCinemasUseCase.CinemaData]

    def __init__(self, cinema_repository: CinemaRepository) -> None:
        """Initialize the use case.

        Args:
            cinema_repository: A repository for querying cinemas.
        """
        self.cinema_repository = cinema_repository

    async def execute(self, request: InputData) -> OutputData:
        """List cinemas, optionally filtered by name.

        Args:
            request: The input data containing optional name filter.

        Returns:
            The output data containing matching cinemas.
        """
        cinemas = await self.cinema_repository.find_all(
            name_filter=request.name,
        )

        cinema_data = [
            self.CinemaData(
                id=str(c.id),
                name=c.name,
                address=c.address,
                city=c.city,
                website=c.website,
            )
            for c in cinemas
        ]

        return self.OutputData(cinemas=cinema_data)
