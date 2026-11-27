"""List registered sources query."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from marquise.application.readers import SourceDefinitionReader

logger = logging.getLogger(__name__)


class ListSourcesQuery:
    """Query every registered showtime source's display data."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for listing sources (no parameters)."""

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data containing the registered sources, ordered by name."""

        sources: list[SourceDefinitionReader.SourceDefinitionData]

    def __init__(self, source_definition_reader: SourceDefinitionReader) -> None:
        """Initialize with a reader for source definition display data."""
        self._source_definition_reader = source_definition_reader

    async def execute(self, input_data: InputData) -> OutputData:
        """List every registered source.

        Args:
            input_data: The input data (no parameters).

        Returns:
            Every registered source's display data, ordered by name.
        """
        sources = await self._source_definition_reader.list_all()
        logger.debug("Listed %d registered sources", len(sources))
        return self.OutputData(sources=sources)
