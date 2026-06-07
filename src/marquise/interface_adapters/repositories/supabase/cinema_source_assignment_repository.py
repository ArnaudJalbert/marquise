"""Supabase repository implementation of CinemaSourceAssignmentRepository.

Adapts a ``CinemaSourceAssignmentGateway`` (infrastructure) into the
``CinemaSourceAssignmentRepository`` interface (application).  No SQL, no
asyncpg — pure entity mapping.
"""

from __future__ import annotations

from typing import Optional

from marquise.application.exceptions import (
    CinemaSourceAssignmentAlreadyExistsError,
)
from marquise.application.repositories import CinemaSourceAssignmentRepository
from marquise.domain.entities import CinemaSourceAssignment
from marquise.domain.value_objects import CinemaId, SourceName
from marquise.interface_adapters.repositories.protocols.cinema import GatewayError
from marquise.interface_adapters.repositories.protocols.cinema_source_assignment import (  # noqa: E501
    CinemaSourceAssignmentGateway,
)


class SupabaseCinemaSourceAssignmentRepository(CinemaSourceAssignmentRepository):
    """Cinema-source assignment repository backed by Supabase PostgreSQL.

    Parameters
    ----------
    gateway:
        A data gateway that implements ``CinemaSourceAssignmentGateway``.
    """

    def __init__(self, gateway: CinemaSourceAssignmentGateway) -> None:
        """Initialize the repository.

        Args:
            gateway: The low-level data gateway for database operations.
        """
        self._gateway = gateway

    async def assign(
        self, assignment: CinemaSourceAssignment
    ) -> CinemaSourceAssignment:
        """Persist a cinema-source assignment via the gateway.

        Args:
            assignment: The assignment domain entity to save.

        Returns:
            The saved assignment.

        Raises:
            CinemaSourceAssignmentAlreadyExistsError: If the cinema already
                has a different source assigned (gateway-level conflict).
        """
        try:
            data = await self._gateway.assign(
                cinema_id=str(assignment.cinema_id),
                source_name=str(assignment.source_name),
            )
        except GatewayError as exc:
            raise CinemaSourceAssignmentAlreadyExistsError(str(exc)) from exc
        return self._to_entity(data)

    async def unassign(self, cinema_id: CinemaId) -> bool:
        """Remove the source assignment for a cinema.

        Args:
            cinema_id: The cinema to unassign.

        Returns:
            True if an assignment was removed, False if none existed.
        """
        return await self._gateway.unassign(cinema_id=str(cinema_id))

    async def find_by_cinema_id(
        self, cinema_id: CinemaId
    ) -> Optional[CinemaSourceAssignment]:
        """Find the source assignment for a given cinema.

        Args:
            cinema_id: The cinema to look up.

        Returns:
            The matching assignment, or None if not found.
        """
        data = await self._gateway.find_by_cinema_id(cinema_id=str(cinema_id))
        return self._to_entity(data) if data is not None else None

    async def find_all(self) -> list[CinemaSourceAssignment]:
        """Retrieve all cinema-source assignments.

        Returns:
            A list of all assignment entities.
        """
        rows = await self._gateway.find_all()
        return [self._to_entity(row) for row in rows]

    @staticmethod
    def _to_entity(data: dict) -> CinemaSourceAssignment:
        """Map a raw gateway dict to a CinemaSourceAssignment domain entity.

        Args:
            data: The dict returned by the gateway.

        Returns:
            A new CinemaSourceAssignment entity populated with the dict values.
        """
        return CinemaSourceAssignment(
            cinema_id=CinemaId(value=data["cinema_id"]),
            source_name=SourceName(value=data["source_name"]),
        )
