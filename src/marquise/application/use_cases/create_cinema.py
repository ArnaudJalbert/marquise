"""Create cinema use case."""

from __future__ import annotations

from uuid import uuid4

from marquise.application.dtos.cinema import CreateCinemaRequest, CreateCinemaResponse
from marquise.application.exceptions import CinemaIdAlreadyExistsError
from marquise.application.repositories import CinemaRepository
from marquise.domain.entities import Cinema
from marquise.domain.exceptions import CinemaAlreadyExistsError
from marquise.domain.value_objects import CinemaId


class CreateCinemaUseCase:
    """Use case for creating a new cinema."""

    def __init__(self, cinema_repository: CinemaRepository) -> None:
        self.cinema_repository = cinema_repository

    async def execute(self, request: CreateCinemaRequest) -> CreateCinemaResponse:
        """Create a new cinema.

        Generates a unique ID, validates no duplicate name+address,
        saves the cinema, and returns the response.
        """
        existing = await self.cinema_repository.find_by_name_and_address(
            name=request.name,
            address=request.address,
        )
        if existing is not None:
            raise CinemaAlreadyExistsError(
                f"A cinema with name '{request.name}' and address '{request.address}' already exists"
            )

        cinema_id = CinemaId(value=str(uuid4()))
        if await self.cinema_repository.exists_by_id(cinema_id):
            msg = f"Generated ID {cinema_id} already exists"
            raise CinemaIdAlreadyExistsError(msg)

        cinema = Cinema(
            id=cinema_id,
            name=request.name,
            address=request.address,
            city=request.city,
        )

        saved = await self.cinema_repository.save(cinema)

        return CreateCinemaResponse(
            id=str(saved.id),
            name=saved.name,
            address=saved.address,
            city=saved.city,
        )
