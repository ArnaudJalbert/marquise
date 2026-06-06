"""Supabase repository implementation of CinemaRepository.

Adapts a ``CinemaGateway`` (infrastructure) into the ``CinemaRepository``
interface (application).  No SQL, no asyncpg — pure entity mapping.
"""

from __future__ import annotations

from typing import Optional

from marquise.application.exceptions import CinemaIdAlreadyExistsError
from marquise.application.repositories import CinemaRepository
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId
from marquise.interface_adapters.repositories.protocols.cinema import (
    CinemaGateway,
    GatewayError,
)


class SupabaseCinemaRepository(CinemaRepository):
    """Cinema repository backed by a Supabase PostgreSQL database.

    Parameters
    ----------
    gateway:
        A data gateway that implements ``CinemaGateway``.
    """

    def __init__(self, gateway: CinemaGateway) -> None:
        """Initialize the repository.

        Args:
            gateway: The low-level data gateway for database operations.
        """
        self._gateway = gateway

    async def save(self, cinema: Cinema) -> Cinema:
        """Persist a cinema via the gateway and return the mapped entity.

        Args:
            cinema: The cinema domain entity to save.

        Returns:
            The saved cinema with server-assigned fields.

        Raises:
            CinemaIdAlreadyExistsError: If a cinema with the same ID already
                exists in the database.
        """
        try:
            data = await self._gateway.save(
                cinema_id=str(cinema.id),
                name=cinema.name,
                address=cinema.address,
                city=cinema.city,
            )
        except GatewayError as exc:
            raise CinemaIdAlreadyExistsError(str(exc)) from exc
        return self._to_entity(data)

    async def find_by_id(self, cinema_id: CinemaId) -> Optional[Cinema]:
        """Retrieve a cinema by ID.

        Args:
            cinema_id: The unique identifier of the cinema.

        Returns:
            The matching cinema entity, or None if not found.
        """
        data = await self._gateway.find_by_id(cinema_id=str(cinema_id))
        return self._to_entity(data) if data is not None else None

    async def find_by_name_and_address(
        self, name: str, address: Optional[str]
    ) -> Optional[Cinema]:
        """Find a cinema by its exact name and address.

        Args:
            name: The cinema name.
            address: The cinema address (may be None).

        Returns:
            The matching cinema entity, or None if not found.
        """
        data = await self._gateway.find_by_name_and_address(name=name, address=address)
        return self._to_entity(data) if data is not None else None

    async def exists_by_id(self, cinema_id: CinemaId) -> bool:
        """Check whether a cinema exists with the given ID.

        Args:
            cinema_id: The ID to check for.

        Returns:
            True if a cinema with that ID exists, False otherwise.
        """
        return await self._gateway.exists_by_id(cinema_id=str(cinema_id))

    @staticmethod
    def _to_entity(data: dict) -> Cinema:
        """Map a raw gateway dict to a Cinema domain entity.

        Args:
            data: The dict returned by the gateway.

        Returns:
            A new Cinema entity populated with the dict values.
        """
        return Cinema(
            id=CinemaId(value=data["id"]),
            name=data["name"],
            address=data["address"],
            city=data["city"],
        )
