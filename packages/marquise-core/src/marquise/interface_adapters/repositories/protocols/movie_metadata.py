"""Persistence seams for metadata rows and the separately owned merge transaction."""

from datetime import datetime
from typing import Protocol

from marquise.application.movie_workflows import (
    MergeMoviesInputData,
    MergeMoviesOutputData,
)
from marquise.interface_adapters.repositories.protocols.base import GatewayError


class MovieMetadataConflictError(GatewayError):
    """A stale snapshot or uniqueness conflict prevented an atomic write."""


class MovieMetadataGateway(Protocol):
    """Raw persistence operations. TMDB IDs are explicitly provider-scoped."""

    async def get(self, movie_id: str) -> dict | None:
        """Read a movie and its reference revision."""
        ...

    async def find_by_tmdb_id(self, tmdb_id: str) -> dict | None:
        """Read only the explicitly supported TMDB identity."""
        ...

    async def list_tmdb_movies(self) -> list[dict]:
        """Read linked movies in stable ID order, including legacy pending rows."""
        ...

    async def update_metadata(
        self,
        movie_id: str,
        revision: str,
        values: dict,
        tmdb_id: str,
        enriched_at: datetime,
    ) -> dict:
        """Patch selected fields and completion time atomically by stable ID."""
        ...


class MovieMergeGateway(Protocol):
    """Injected merge implementation owned by #356, not metadata persistence."""

    async def merge(self, request: MergeMoviesInputData) -> MergeMoviesOutputData:
        """Preview or apply the independently implemented guarded transaction."""
        ...
