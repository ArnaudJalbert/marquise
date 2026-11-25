"""Query one cinema's display data without constructing domain entities."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.readers import CinemaReader


class GetCinemaQuery:
    """Retrieve one cinema projection through an injected reader."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for fetching a cinema.

        Attributes:
            cinema_id: The unique identifier of the cinema.
        """

        cinema_id: str

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If cinema_id is empty or whitespace-only.
            """
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """The retrieved cinema's output data.

        Attributes:
            id: Unique identifier of the cinema.
            name: Display name of the cinema.
            address: Street address (optional).
            city: City where the cinema is located (optional).
            website: Cinema's website URL (optional).
        """

        id: str
        name: str
        address: str | None = None
        city: str | None = None
        website: str | None = None

    def __init__(self, cinema_reader: CinemaReader) -> None:
        """Initialize the query.

        Args:
            cinema_reader: A reader for cinema display data.
        """
        self._cinema_reader = cinema_reader

    async def execute(self, input_data: InputData) -> OutputData:
        """Retrieve a cinema by its ID.

        Args:
            input_data: The input data containing the cinema ID.

        Returns:
            The output data describing the cinema.

        Raises:
            CinemaNotFoundError: If no cinema with the given ID exists.
        """
        cinema = await self._cinema_reader.find_by_id(input_data.cinema_id)
        if cinema is None:
            raise CinemaNotFoundError(
                f"A cinema with ID '{input_data.cinema_id}' was not found"
            )
        return self.OutputData(
            id=cinema.id,
            name=cinema.name,
            address=cinema.address,
            city=cinema.city,
            website=cinema.website,
        )
