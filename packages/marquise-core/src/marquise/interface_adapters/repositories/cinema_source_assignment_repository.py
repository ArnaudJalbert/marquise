"""Postgres repository implementation of CinemaSourceAssignmentRepository.

Adapts a ``CinemaSourceAssignmentGateway`` (infrastructure) into the
``CinemaSourceAssignmentRepository`` interface (application).  No SQL, no
asyncpg — pure entity mapping.
"""

from __future__ import annotations

from marquise.application.exceptions import (
    CinemaSourceAssignmentAlreadyExistsError,
)
from marquise.application.repositories import CinemaSourceAssignmentRepository
from marquise.domain.entities import CinemaSourceAssignment, SourceDefinition
from marquise.domain.value_objects import CinemaId, SourceName
from marquise.interface_adapters.gateways.base import GatewayError
from marquise.interface_adapters.gateways.cinema_source_assignment import (
    CinemaSourceAssignmentGateway,
)
from marquise.interface_adapters.mappers import extract_prefixed, to_cinema


def _dict_to_source_definition(data: dict) -> SourceDefinition:
    """Convert a prefixed source definition dict into a SourceDefinition entity."""
    return SourceDefinition(
        name=SourceName(value=data["name"]),
        display_name=data["display_name"],
        description=data.get("description"),
    )


class PostgresCinemaSourceAssignmentRepository(CinemaSourceAssignmentRepository):
    """Cinema-source assignment repository backed by PostgreSQL.

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
            await self._gateway.assign(
                cinema_id=str(assignment.cinema.id),
                source_name=str(assignment.source.name),
            )
        except GatewayError as exc:
            raise CinemaSourceAssignmentAlreadyExistsError(str(exc)) from exc
        return CinemaSourceAssignment(
            cinema=assignment.cinema,
            source=assignment.source,
        )

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
    ) -> CinemaSourceAssignment | None:
        """Find the source assignment for a given cinema.

        Args:
            cinema_id: The cinema to look up.

        Returns:
            The matching assignment, or None if not found.
        """
        data = await self._gateway.find_by_cinema_id(cinema_id=str(cinema_id))
        return self._to_entity(data) if data is not None else None

    @staticmethod
    def _to_entity(data: dict) -> CinemaSourceAssignment:
        """Map a raw gateway dict to a CinemaSourceAssignment domain entity.

        Args:
            data: The dict returned by the gateway (with joined cinema and
                source definition data prefixed with ``cinema__`` and
                ``source__``).

        Returns:
            A new CinemaSourceAssignment entity populated with the dict values.
        """
        cinema = to_cinema(extract_prefixed(data, "cinema__"))
        source = _dict_to_source_definition(extract_prefixed(data, "source__"))
        return CinemaSourceAssignment(
            cinema=cinema,
            source=source,
        )
