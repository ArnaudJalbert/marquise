"""List cinemas use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.repositories import CinemaRepository


class ListCinemasUseCase:
    """Use case for listing cinemas with optional name filtering."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing cinemas.

        Attributes:
            name: Optional name filter (substring, case-insensitive).
            page: Page number (1-based). Ignored when size is None.
            size: Max number of items per page. If None, all matching
                cinemas are returned unbounded (page is ignored).
        """

        name: str | None = None
        page: int = 1
        size: int | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If name is provided but empty or whitespace-only,
                    if size is provided but not positive, or if page is less
                    than 1.
            """
            if self.name is not None and not self.name.strip():
                raise ValueError("name must not be empty when provided")
            if self.size is not None and self.size < 1:
                raise ValueError("size must be positive when provided")
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
            cinemas: The page of matching cinemas.
            total: Total number of cinemas matching the filter, ignoring
                limit/offset.
        """

        cinemas: list[ListCinemasUseCase.CinemaData]
        total: int

        def __post_init__(self) -> None:
            """Validate output data.

            Raises:
                ValueError: If total is negative.
            """
            if self.total < 0:
                raise ValueError("total must not be negative")

    def __init__(self, cinema_repository: CinemaRepository) -> None:
        """Initialize the use case.

        Args:
            cinema_repository: A repository for querying cinemas.
        """
        self.cinema_repository = cinema_repository

    async def execute(self, request: InputData) -> OutputData:
        """List cinemas, optionally filtered by name and paginated.

        Args:
            request: The input data containing optional name filter and
                pagination parameters.

        Returns:
            The output data containing the matching page of cinemas and the
            total count.
        """
        if request.size is not None:
            limit = request.size
            offset = (request.page - 1) * request.size
        else:
            limit = None
            offset = 0

        page = await self.cinema_repository.find_all(
            name_filter=request.name,
            limit=limit,
            offset=offset,
        )

        cinema_data = [
            self.CinemaData(
                id=str(c.id),
                name=c.name,
                address=c.address,
                city=c.city,
                website=c.website,
            )
            for c in page.items
        ]

        return self.OutputData(cinemas=cinema_data, total=page.total)
