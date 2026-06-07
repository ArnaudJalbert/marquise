"""Create source use case."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from marquise.application.exceptions import SourceAlreadyExistsError
from marquise.application.repositories import SourceDefinitionRepository
from marquise.domain.entities import SourceDefinition
from marquise.domain.value_objects import SourceName


class CreateSourceUseCase:
    """Use case for registering a new showtime source."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for creating a new source.

        Attributes:
            name: Unique machine name for the source (e.g. ``'cineplex'``).
            display_name: Human-readable label (e.g. ``'Cineplex'``).
            description: Optional longer description.
        """

        name: str
        display_name: str
        description: Optional[str] = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If ``name`` or ``display_name`` is empty.
            """
            if not self.name.strip():
                raise ValueError("name must not be empty")
            if not self.display_name.strip():
                raise ValueError("display_name must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after successful source creation.

        Attributes:
            name: The unique machine name of the source.
            display_name: The human-readable label.
            description: Optional longer description.
        """

        name: str
        display_name: str
        description: Optional[str] = None

        def __post_init__(self) -> None:
            """Validate output data.

            Raises:
                ValueError: If ``name`` or ``display_name`` is empty.
            """
            if not self.name.strip():
                raise ValueError("name must not be empty")
            if not self.display_name.strip():
                raise ValueError("display_name must not be empty")

    def __init__(self, source_repository: SourceDefinitionRepository) -> None:
        """Initialize the use case.

        Args:
            source_repository: A repository for persisting source definitions.
        """
        self.source_repository = source_repository

    async def execute(self, request: InputData) -> OutputData:
        """Create a new source definition.

        Args:
            request: The input data for source creation.

        Returns:
            The output data containing the created source details.

        Raises:
            SourceAlreadyExistsError: If a source with the same name already exists.
        """
        source_name = SourceName(value=request.name)

        existing = await self.source_repository.find_by_name(source_name)
        if existing is not None:
            raise SourceAlreadyExistsError(
                f"A source with name '{request.name}' already exists"
            )

        source = SourceDefinition(
            name=source_name,
            display_name=request.display_name,
            description=request.description,
        )

        saved = await self.source_repository.save(source)

        return self.OutputData(
            name=str(saved.name),
            display_name=saved.display_name,
            description=saved.description,
        )
