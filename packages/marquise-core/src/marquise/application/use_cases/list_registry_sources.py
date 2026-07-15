"""List registry sources use case.

Lists showtime source gateways registered in the code-level
``SourceRegistry``.
"""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.repositories import SourceRegistryQuery


class ListRegistrySourcesUseCase:
    """Use case for listing available source gateways from the registry."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing registry sources (no parameters)."""

        def __post_init__(self) -> None:
            """Validate input data (no-op, no parameters)."""

    @dataclass(frozen=True, slots=True)
    class SourceEntry:
        """A single source entry from the registry.

        Attributes:
            name: Unique machine name (e.g. ``"cinemacinema"``).
        """

        name: str

        def __post_init__(self) -> None:
            if not self.name.strip():
                raise ValueError("name must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing the list of registry sources.

        Attributes:
            sources: The list of sources available in the registry.
        """

        sources: list[ListRegistrySourcesUseCase.SourceEntry]

    def __init__(self, registry: SourceRegistryQuery) -> None:
        """Initialize the use case.

        Args:
            registry: A ``SourceRegistryQuery`` implementation for
                querying available source gateways.
        """
        self._registry = registry

    async def execute(self, request: InputData) -> OutputData:
        """List all sources available in the code-level registry.

        Args:
            request: The input data (no parameters).

        Returns:
            The output data containing registry source entries.
        """
        available = self._registry.list_available()
        entries = [self.SourceEntry(name=name) for name in sorted(available)]
        return self.OutputData(sources=entries)
