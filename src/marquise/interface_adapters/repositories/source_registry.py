"""Registry mapping source names to concrete ShowtimeSource implementations.

Wired by the dependency injection container at startup.  Each source has its
own specific method signature — only ``fetch_showtimes`` is guaranteed.
"""

from __future__ import annotations

from marquise.application.repositories import (
    RegistrySourceEntry,
    SourceRegistryQuery,
)
from marquise.interface_adapters.repositories.protocols.showtime_source import (
    ShowtimeSource,
)


class SourceRegistry(SourceRegistryQuery):
    """Maps source names to concrete ``ShowtimeSource`` instances.

    Typical wiring in the DI container::

        registry = SourceRegistry()
        registry.register("cinemacinema", CinemaCinemaSource())

    Each registered source has its own method signature, so callers cast
    explicitly::

        source = registry.get("cinemacinema")
        results = await source.fetch_showtimes(cinema_name="beaubien")
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._sources: dict[str, ShowtimeSource] = {}

    def register(self, name: str, source: ShowtimeSource) -> None:
        """Register a showtime source gateway under a given name.

        Args:
            name: The unique source name (e.g. ``"cinemacinema"``).
            source: A ``ShowtimeSource`` implementor.

        Raises:
            ValueError: If a source with the given ``name`` is already registered.
        """
        if name in self._sources:
            raise ValueError(f"A source with name '{name}' is already registered")
        self._sources[name] = source

    def get(self, name: str) -> ShowtimeSource:
        """Retrieve a registered source gateway by name.

        Args:
            name: The unique source name.

        Returns:
            The registered ``ShowtimeSource`` implementor.

        Raises:
            KeyError: If no source is registered under ``name``.
        """
        if name not in self._sources:
            raise KeyError(f"No source registered with name '{name}'")
        return self._sources[name]

    def list_available(self) -> dict[str, RegistrySourceEntry]:
        """Return all registered sources with their names.

        Returns:
            A mapping of source name to ``RegistrySourceEntry``.
        """
        return {name: RegistrySourceEntry(name=name) for name in self._sources}
