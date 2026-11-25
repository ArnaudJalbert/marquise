"""Adapter mapping source definition rows to application read models."""

from __future__ import annotations

from marquise.application.readers import SourceDefinitionReader
from marquise.interface_adapters.readers.source_definition_read_gateway import (
    SourceDefinitionReadGateway,
)


class PostgresSourceDefinitionReader(SourceDefinitionReader):
    """Map rows supplied by an injected source definition read gateway."""

    def __init__(self, gateway: SourceDefinitionReadGateway) -> None:
        """Initialize with the plain-data gateway."""
        self._gateway = gateway

    async def list_all(self) -> list[SourceDefinitionReader.SourceDefinitionData]:
        """Return every registered source's display data, ordered by name."""
        rows = await self._gateway.list_all()
        return [self.SourceDefinitionData(**row) for row in rows]
