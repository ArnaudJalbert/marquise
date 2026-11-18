"""List every cinema use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.repositories import CinemaRepository


class ListAllCinemasUseCase:
    """Use case for listing every cinema, optionally filtered by name."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing every cinema.

        Attributes:
            name: Optional name filter (substring, case-insensitive).
        """

        name: str | None = None

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
        address: str | None = None
        city: str | None = None
        website: str | None = None

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing every matching cinema.

        Attributes:
            cinemas: Every cinema matching the filter.
        """

        cinemas: list[ListAllCinemasUseCase.CinemaData]

    def __init__(self, cinema_repository: CinemaRepository) -> None:
        """Initialize the use case.

        Args:
            cinema_repository: A repository for querying cinemas.
        """
        self.cinema_repository = cinema_repository

    async def execute(self, input_data: InputData) -> OutputData:
        """List every cinema, optionally filtered by name.

        Args:
            input_data: The input data containing the optional name filter.

        Returns:
            The output data containing every matching cinema.
        """
        page = await self.cinema_repository.find_all(name_filter=input_data.name)
        return self.OutputData(
            cinemas=[
                self.CinemaData(
                    id=str(cinema.id),
                    name=cinema.name,
                    address=cinema.address,
                    city=cinema.city,
                    website=cinema.website,
                )
                for cinema in page.items
            ]
        )
