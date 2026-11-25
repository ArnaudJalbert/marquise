"""Get cinema source query."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from marquise.application.exceptions import CinemaSourceAssignmentNotFoundError
from marquise.application.readers import CinemaSourceAssignmentReader

logger = logging.getLogger(__name__)


class GetCinemaSourceQuery:
    """Retrieve the source assigned to a cinema through an injected reader."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for retrieving a cinema's source.

        Attributes:
            cinema_id: The ID of the cinema to look up.
        """

        cinema_id: str

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                TypeError: If ``cinema_id`` is not a string.
                ValueError: If ``cinema_id`` is empty or whitespace-only.
            """
            if not isinstance(self.cinema_id, str):
                raise TypeError("cinema_id must be a string")
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing the assigned source information.

        Attributes:
            cinema_id: The ID of the cinema.
            source_name: The machine name of the assigned source.
            source_display_name: The human-readable label of the source.
        """

        cinema_id: str
        source_name: str
        source_display_name: str

    def __init__(self, reader: CinemaSourceAssignmentReader) -> None:
        """Initialize with the cinema-source assignment reader."""
        self._reader = reader

    async def execute(self, input_data: InputData) -> OutputData:
        """Retrieve the source assigned to a cinema.

        Args:
            input_data: The input data containing the cinema ID.

        Returns:
            The output data with the assigned source details.

        Raises:
            CinemaSourceAssignmentNotFoundError: If no assignment exists
                for the given cinema.
        """
        assignment = await self._reader.find_by_cinema_id(input_data.cinema_id)
        if assignment is None:
            raise CinemaSourceAssignmentNotFoundError(
                f"No source assignment found for cinema '{input_data.cinema_id}'"
            )
        logger.debug(
            "Cinema %s reads from source %s",
            assignment.cinema_id,
            assignment.source_name,
        )
        return self.OutputData(
            cinema_id=assignment.cinema_id,
            source_name=assignment.source_name,
            source_display_name=assignment.source_display_name,
        )
