"""List sources use case."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from marquise.application.repositories import SourceDefinitionRepository


class ListSourcesUseCase:
    """Use case for listing all registered showtime sources."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing sources (no parameters)."""

        def __post_init__(self) -> None:
            """Validate input data (no-op, no parameters)."""

    @dataclass(frozen=True, slots=True)
    class SourceData:
        """A single source's output data.

        Attributes:
            name: The unique machine name.
            display_name: The human-readable label.
            description: Optional longer description.
        """

        name: str
        display_name: str
        description: Optional[str] = None

        def __post_init__(self) -> None:
            """Validate source data.

            Raises:
                ValueError: If ``name`` or ``display_name`` is empty.
            """
            if not self.name.strip():
                raise ValueError("name must not be empty")
            if not self.display_name.strip():
                raise ValueError("display_name must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing the list of sources.

        Attributes:
            sources: The list of registered sources.
        """

        sources: list[ListSourcesUseCase.SourceData]

        def __post_init__(self) -> None:
            """Validate output data.

            Raises:
                ValueError: If sources is None.
            """
            if self.sources is None:
                raise ValueError("sources must not be None")

    def __init__(self, source_repository: SourceDefinitionRepository) -> None:
        """Initialize the use case.

        Args:
            source_repository: A repository for querying source definitions.
        """
        self.source_repository = source_repository

    async def execute(self, request: InputData) -> OutputData:
        """List all registered sources.

        Args:
            request: The input data (no parameters).

        Returns:
            The output data containing all source definitions.
        """
        sources = await self.source_repository.find_all()

        source_data = [
            self.SourceData(
                name=str(s.name),
                display_name=s.display_name,
                description=s.description,
            )
            for s in sources
        ]

        return self.OutputData(sources=source_data)
