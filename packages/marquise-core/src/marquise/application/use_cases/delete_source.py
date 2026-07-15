"""Delete source use case."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.exceptions import SourceNotFoundError
from marquise.application.repositories import SourceDefinitionRepository
from marquise.domain.value_objects import SourceName


class DeleteSourceUseCase:
    """Use case for removing a registered showtime source."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for deleting a source.

        Attributes:
            source_name: The unique machine name of the source to delete.
        """

        source_name: str

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If ``source_name`` is empty or whitespace-only.
            """
            if not self.source_name.strip():
                raise ValueError("source_name must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after successful source deletion.

        Attributes:
            source_name: The name of the deleted source.
        """

        source_name: str

    def __init__(self, source_repository: SourceDefinitionRepository) -> None:
        """Initialize the use case.

        Args:
            source_repository: A repository for source definition persistence.
        """
        self.source_repository = source_repository

    async def execute(self, request: InputData) -> OutputData:
        """Delete a source by its name.

        Args:
            request: The input data containing the source name.

        Returns:
            The output data containing the deleted source's name.

        Raises:
            SourceNotFoundError: If no source with the given name exists.
        """
        source_name = SourceName(value=request.source_name)
        deleted = await self.source_repository.delete(source_name)

        if not deleted:
            raise SourceNotFoundError(
                f"A source with name '{request.source_name}' was not found"
            )

        return self.OutputData(source_name=request.source_name)
