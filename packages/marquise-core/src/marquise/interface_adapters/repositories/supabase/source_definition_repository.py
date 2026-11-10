"""Supabase repository implementation of SourceDefinitionRepository.

Adapts a ``SourceDefinitionGateway`` (infrastructure) into the
``SourceDefinitionRepository`` interface (application).  No SQL, no
asyncpg — pure entity mapping.
"""

from __future__ import annotations

from marquise.application.exceptions import (
    SourceAlreadyExistsError,
)
from marquise.application.repositories import SourceDefinitionRepository
from marquise.domain.entities import SourceDefinition
from marquise.domain.value_objects import SourceName
from marquise.interface_adapters.repositories.protocols.cinema import GatewayError
from marquise.interface_adapters.repositories.protocols.source_definition import (
    SourceDefinitionGateway,
)


class SupabaseSourceDefinitionRepository(SourceDefinitionRepository):
    """Source definition repository backed by a Supabase PostgreSQL database.

    Parameters
    ----------
    gateway:
        A data gateway that implements ``SourceDefinitionGateway``.
    """

    def __init__(self, gateway: SourceDefinitionGateway) -> None:
        """Initialize the repository.

        Args:
            gateway: The low-level data gateway for database operations.
        """
        self._gateway = gateway

    async def save(self, source: SourceDefinition) -> SourceDefinition:
        """Persist a source definition via the gateway.

        Args:
            source: The source definition domain entity to save.

        Returns:
            The saved source definition.

        Raises:
            SourceAlreadyExistsError: If a source with the same name already
                exists in the database.
        """
        try:
            data = await self._gateway.save(
                name=str(source.name),
                display_name=source.display_name,
                description=source.description,
            )
        except GatewayError as exc:
            raise SourceAlreadyExistsError(str(exc)) from exc
        return self._to_entity(data)

    async def find_by_name(self, name: SourceName) -> SourceDefinition | None:
        """Retrieve a source definition by name.

        Args:
            name: The unique machine name.

        Returns:
            The matching source definition entity, or None if not found.
        """
        data = await self._gateway.find_by_name(name=str(name))
        return self._to_entity(data) if data is not None else None

    async def find_all(self) -> list[SourceDefinition]:
        """Retrieve all registered source definitions.

        Returns:
            A list of all source definition entities.
        """
        rows = await self._gateway.find_all()
        return [self._to_entity(row) for row in rows]

    async def delete(self, name: SourceName) -> bool:
        """Delete a source definition by its name.

        Args:
            name: The unique machine name of the source to delete.

        Returns:
            True if a source was deleted, False if none was found.
        """
        return await self._gateway.delete(name=str(name))

    @staticmethod
    def _to_entity(data: dict) -> SourceDefinition:
        """Map a raw gateway dict to a SourceDefinition domain entity.

        Args:
            data: The dict returned by the gateway.

        Returns:
            A new SourceDefinition entity populated with the dict values.
        """
        return SourceDefinition(
            name=SourceName(value=data["name"]),
            display_name=data["display_name"],
            description=data.get("description"),
        )
