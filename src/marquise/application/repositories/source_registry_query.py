"""Application-layer interface for querying available source gateways.

Defines the contract that the ``ListRegistrySourcesUseCase`` depends on.
The concrete ``SourceRegistry`` in ``interface_adapters/repositories/``
implements this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from marquise.domain.entities import Cinema, SourceDefinition


@dataclass(frozen=True, slots=True)
class RegistrySourceEntry:
    """A source registered in the code-level registry.

    Attributes:
        name: Unique machine name (e.g. ``"cinemacinema"``).
    """

    name: str


@dataclass(frozen=True, slots=True)
class ShowtimeRow:
    """A single showtime row returned by a source.

    Attributes:
        movie_title: The title of the movie.
        showtime: The showtime as a timezone-aware datetime.
    """

    movie_title: str
    showtime: datetime


class SourceRegistryQuery(ABC):
    """Interface for listing available showtime source gateways."""

    @abstractmethod
    def list_available(self) -> dict[str, RegistrySourceEntry]:
        """Return all registered sources with their metadata.

        Returns:
            A mapping of source name to ``RegistrySourceEntry``.
        """
        ...

    @abstractmethod
    async def fetch_showtimes(
        self,
        cinema: Cinema,
        source_definition: SourceDefinition,
        start_date: datetime,
        end_date: datetime,
    ) -> list[ShowtimeRow]:
        """Fetch showtimes from a registered source.

        Args:
            cinema: The cinema to fetch showtimes for.
            source_definition: The source definition identifying which
                registered source to use.
            start_date: Start of date range (inclusive).
            end_date: End of date range (inclusive).

        Returns:
            A list of ``ShowtimeRow`` dataclass instances.

        Raises:
            KeyError: If no source is registered for the given
                ``source_definition`` name.
        """
        ...
