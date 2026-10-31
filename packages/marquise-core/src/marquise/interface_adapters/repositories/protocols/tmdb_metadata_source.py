"""Plain TMDB transport port for metadata mapping."""

from typing import Protocol

from marquise.application.metadata import MetadataBatch, MetadataFailure


class TmdbMetadataError(Exception):
    """Sanitized provider failure crossing the transport boundary."""

    def __init__(self, failure: MetadataFailure) -> None:
        super().__init__(failure.message)
        self.failure = failure


class TmdbMetadataSource(Protocol):
    """Retrieve provider JSON, with pagination owned by infrastructure."""

    async def get(self, path: str, params: dict[str, str] | None = None) -> dict:
        """Retrieve one endpoint or raise a sanitized TmdbMetadataError."""
        ...

    async def pages(self, path: str, params: dict[str, str]) -> MetadataBatch[dict]:
        """Retrieve ordered rows, retaining partial results on failure."""
        ...
