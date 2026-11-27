"""Command: create a cinema with a unique name and address."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from marquise.application.exceptions import CinemaAlreadyExistsError
from marquise.application.repositories import CinemaRepository
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId

logger = logging.getLogger(__name__)


class CreateCinemaCommand:
    """Create a cinema unless one with the same name and address exists."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for creating a new cinema.

        Attributes:
            name: Display name of the cinema (required, non-empty).
            address: Street address (optional).
            city: City where the cinema is located (optional).
            website: Cinema's website URL (optional).
        """

        name: str
        address: str | None = None
        city: str | None = None
        website: str | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                TypeError: If a field is not a string, or not None when optional.
                ValueError: If the name is empty or whitespace-only, or if an
                    optional field is provided but whitespace-only.
            """
            if not isinstance(self.name, str):
                raise TypeError("name must be a string")
            if not isinstance(self.address, str | None):
                raise TypeError("address must be a string or None")
            if not isinstance(self.city, str | None):
                raise TypeError("city must be a string or None")
            if not isinstance(self.website, str | None):
                raise TypeError("website must be a string or None")
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
        """Output data returned after successful cinema creation.

        Attributes:
            cinema_id: The generated unique ID of the cinema.
        """

        cinema_id: str

    def __init__(self, cinema_repository: CinemaRepository) -> None:
        """Initialize the command.

        Args:
            cinema_repository: A repository for persisting cinemas.
        """
        self._cinema_repository = cinema_repository

    async def execute(self, input_data: InputData) -> OutputData:
        """Create a cinema unless one with the same name and address exists.

        Args:
            input_data: The details of the cinema to create.

        Returns:
            The ID of the created cinema.

        Raises:
            CinemaAlreadyExistsError: If a cinema with the same name
                and address already exists.
        """
        cinema = Cinema(
            id=CinemaId(value=uuid4().hex),
            name=input_data.name,
            address=input_data.address,
            city=input_data.city,
            website=input_data.website,
        )
        await self._require_unique_name_and_address(cinema)
        saved = await self._cinema_repository.save(cinema)
        logger.info("Created cinema %s", saved.id.value)
        return self.OutputData(cinema_id=saved.id.value)

    async def _require_unique_name_and_address(self, cinema: Cinema) -> None:
        existing = await self._cinema_repository.find_by_name_and_address(
            name=cinema.name,
            address=cinema.address,
        )
        if existing is not None:
            raise CinemaAlreadyExistsError(
                f"A cinema with name '{cinema.name}' already exists."
            )
