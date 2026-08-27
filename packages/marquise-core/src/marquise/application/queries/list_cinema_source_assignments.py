"""List cinema-source assignments query."""

from __future__ import annotations

from dataclasses import dataclass

from marquise.application.readers import (
    CinemaSourceAssignmentData,
    CinemaSourceAssignmentReader,
)


class ListCinemaSourceAssignmentsQuery:
    """Query every cinema-source assignment's display data."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing assignments (no parameters)."""

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing cinema-source assignments."""

        assignments: list[CinemaSourceAssignmentData]

    def __init__(self, reader: CinemaSourceAssignmentReader) -> None:
        """Initialize with cinema-source assignment reader."""
        self._reader = reader

    async def execute(self, request: InputData) -> OutputData:
        """List cinema-source assignments."""
        return self.OutputData(assignments=await self._reader.list_all())
