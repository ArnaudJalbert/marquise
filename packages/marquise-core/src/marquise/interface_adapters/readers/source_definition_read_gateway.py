"""Gateway contract for source definition display rows."""

from __future__ import annotations

from typing import Protocol


class SourceDefinitionReadGateway(Protocol):
    """Read plain source definition rows without hydrating domain entities."""

    async def list_all(self) -> list[dict]:
        """Return every ``name``, ``display_name`` and ``description`` row by name."""
        ...
