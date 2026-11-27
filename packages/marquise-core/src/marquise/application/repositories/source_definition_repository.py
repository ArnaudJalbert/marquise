"""Abstract repository for source definition persistence."""

from __future__ import annotations

from abc import ABC, abstractmethod

from marquise.domain.entities import SourceDefinition
from marquise.domain.value_objects import SourceName


class SourceDefinitionRepository(ABC):
    """Abstract interface for source definition data persistence."""

    @abstractmethod
    async def save(self, source: SourceDefinition) -> SourceDefinition:
        """Persist a source definition.

        Args:
            source: The source definition to save.

        Returns:
            The saved source definition.
        """
        ...

    @abstractmethod
    async def find_by_name(self, name: SourceName) -> SourceDefinition | None:
        """Retrieve a source definition by its unique name.

        Args:
            name: The source name to look up.

        Returns:
            The matching source definition, or None if not found.
        """
        ...

    @abstractmethod
    async def delete(self, name: SourceName) -> bool:
        """Delete a source definition by its name.

        Args:
            name: The source name to delete.

        Returns:
            True if a source definition was deleted, False otherwise.
        """
        ...
