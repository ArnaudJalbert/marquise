"""List cinemas query."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from marquise.application.page import calculate_page_offset
from marquise.application.readers import CinemaReader

logger = logging.getLogger(__name__)


class ListCinemasQuery:
    """Query one page of cinemas with optional name filtering."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing cinemas.

        Attributes:
            page: Page number (1-based).
            size: Max number of items per page.
            name: Optional name filter (substring, case-insensitive).
        """

        page: int
        size: int
        name: str | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If name is provided but empty or whitespace-only,
                    if size is not positive, or if page is less than 1.
            """
            if self.name is not None and not self.name.strip():
                raise ValueError("name must not be empty when provided")
            if self.size < 1:
                raise ValueError("size must be positive")
            if self.page < 1:
                raise ValueError("page must be at least 1")

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
        """Output data containing the list of cinemas.

        Attributes:
            cinemas: The page of matching cinemas.
            total: Total number of cinemas matching the filter, ignoring
                limit/offset.
        """

        cinemas: list[ListCinemasQuery.CinemaData]
        total: int

    def __init__(self, cinema_reader: CinemaReader) -> None:
        """Initialize the query.

        Args:
            cinema_reader: A reader for cinema display data.
        """
        self._cinema_reader = cinema_reader

    async def execute(self, input_data: InputData) -> OutputData:
        """List one page of cinemas, optionally filtered by name.

        Args:
            input_data: The input data containing optional name filter and
                pagination parameters.

        Returns:
            The output data containing the matching page of cinemas and the
            total count.
        """
        page = await self._cinema_reader.search(
            name_filter=input_data.name,
            limit=input_data.size,
            offset=calculate_page_offset(input_data.page, input_data.size),
        )

        cinema_data = [
            self.CinemaData(
                id=cinema.id,
                name=cinema.name,
                address=cinema.address,
                city=cinema.city,
                website=cinema.website,
            )
            for cinema in page.items
        ]
        logger.debug(
            "Listed %d of %d cinemas on page %d (size %d, name filter: %s)",
            len(cinema_data),
            page.total,
            input_data.page,
            input_data.size,
            input_data.name is not None,
        )

        return self.OutputData(cinemas=cinema_data, total=page.total)
