"""Application-layer interface for querying available source gateways.

Defines the contract that the ``ListRegistrySourcesUseCase`` depends on.
The concrete ``SourceRegistry`` in ``interface_adapters/repositories/``
implements this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegistrySourceEntry:
    """A source registered in the code-level registry.

    Attributes:
        name: Unique machine name (e.g. ``\"cinemacinema\"``).
    """

    name: str


class SourceRegistryQuery(ABC):
    """Interface for listing available showtime source gateways."""

    @abstractmethod
    def list_available(self) -> dict[str, RegistrySourceEntry]:
        """Return all registered sources with their metadata.

        Returns:
            A mapping of source name to ``RegistrySourceEntry``.
        """
        ...
