"""Read port for source definition display data."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class SourceDefinitionReader(ABC):
    """Read source definitions without constructing domain entities."""

    @dataclass(frozen=True, slots=True)
    class SourceDefinitionData:
        """Display data for one registered source."""

        name: str
        display_name: str
        description: str | None

    @abstractmethod
    async def list_all(self) -> list[SourceDefinitionData]:
        """Return every registered source's display data, ordered by name."""
        ...
