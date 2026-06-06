"""Create cinema use case."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import uuid4

from marquise.application.exceptions import CinemaIdAlreadyExistsError
from marquise.application.repositories import CinemaRepository
from marquise.domain.entities import Cinema
from marquise.domain.exceptions import CinemaAlreadyExistsError
from marquise.domain.value_objects import CinemaId


class CreateCinemaUseCase:
    """Use case for creating a new cinema.

    Ensures no duplicate name+address exists, generates a unique ID,
    persists the cinema, and returns the result.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for creating a new cinema.

        Attributes:
            name: Display name of the cinema (required, non-empty).
            address: Street address (optional).
            city: City where the cinema is located (optional).
        """

        name: str
        address: Optional[str] = None
        city: Optional[str] = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If the name is empty or whitespace-only, or if
                    address/city are provided but whitespace-only.
            """
            if not self.name.strip():
                raise ValueError("name must not be empty")
            if self.address is not None and not self.address.strip():
                raise ValueError("address must not be empty when provided")
            if self.city is not None and not self.city.strip():
                raise ValueError("city must not be empty when provided")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after successful cinema creation.

        Attributes:
            id: The generated unique ID of the cinema.
            name: Display name of the cinema.
            address: Street address (optional).
            city: City where the cinema is located (optional).
        """

        id: str
        name: str
        address: Optional[str] = None
        city: Optional[str] = None

        def __post_init__(self) -> None:
            """Validate output data.

            Raises:
                ValueError: If id or name is empty, or if address/city
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

    def __init__(self, cinema_repository: CinemaRepository) -> None:
        """Initialize the use case.

        Args:
            cinema_repository: A repository for persisting cinemas.
        """
        self.cinema_repository = cinema_repository

    async def execute(self, request: InputData) -> OutputData:
        """Create a new cinema.

        Generates a unique ID, validates no duplicate name+address,
        saves the cinema, and returns the response.

        Args:
            request: The input data for cinema creation.

        Returns:
            The output data containing the created cinema details.

        Raises:
            CinemaAlreadyExistsError: If a cinema with the same name
                and address already exists.
            CinemaIdAlreadyExistsError: If the generated UUID collides
                with an existing ID (extremely rare).
        """
        existing = await self.cinema_repository.find_by_name_and_address(
            name=request.name,
            address=request.address,
        )
        if existing is not None:
            raise CinemaAlreadyExistsError(
                f"A cinema with name '{request.name}' "
                f"and address '{request.address}' already exists"
            )

        cinema_id = CinemaId(value=str(uuid4()))

        cinema = Cinema(
            id=cinema_id,
            name=request.name,
            address=request.address,
            city=request.city,
        )

        try:
            saved = await self.cinema_repository.save(cinema)
        except CinemaIdAlreadyExistsError:
            raise CinemaIdAlreadyExistsError(
                f"A cinema with ID '{cinema_id}' already exists — "
                "extremely rare UUID collision. Please retry."
            )

        return self.OutputData(
            id=str(saved.id),
            name=saved.name,
            address=saved.address,
            city=saved.city,
        )
