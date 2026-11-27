"""Source definition gateway protocol for persistence."""

from __future__ import annotations

from typing import Protocol


class SourceDefinitionGateway(Protocol):
    """Protocol for source_definitions table persistence.

    Implementations execute the actual SQL or API calls.  All methods return
    plain dicts or primitives — no domain entities.
    """

    async def save(
        self,
        name: str,
        display_name: str,
        description: str | None = None,
    ) -> dict:
        """Insert a source definition row.

        Args:
            name: Unique machine name.
            display_name: Human-readable label.
            description: Optional longer description.

        Returns:
            The inserted row as a dict.

        Raises:
            GatewayError: If a row with the given ``name`` already exists.
        """
        ...

    async def find_by_name(self, name: str) -> dict | None:
        """Find a source definition by its name.

        Args:
            name: The unique machine name to look up.

        Returns:
            A dict representing the row, or None if not found.
        """
        ...

    async def find_all(self) -> list[dict]:
        """Retrieve all source definition rows.

        Returns:
            A list of dicts representing source definition rows.
        """
        ...

    async def delete(self, name: str) -> bool:
        """Delete a source definition by name.

        Args:
            name: The machine name of the source to delete.

        Returns:
            True if a row was deleted, False otherwise.
        """
        ...
