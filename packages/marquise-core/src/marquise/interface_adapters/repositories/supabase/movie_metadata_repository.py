"""Map raw metadata persistence into the exact application workflow contract."""

from dataclasses import asdict
from datetime import datetime

from marquise.application.movie_workflows import (
    MergeMoviesInputData,
    MergeMoviesOutputData,
    MovieMetadataRepository,
    MovieMetadataSnapshot,
    MovieMetadataValues,
    MovieWorkflowConflictError,
)
from marquise.interface_adapters.repositories.protocols.movie_metadata import (
    MovieMergeGateway,
    MovieMetadataConflictError,
    MovieMetadataGateway,
)


class SupabaseMovieMetadataRepository(MovieMetadataRepository):
    """Metadata adapter with separately injected merge transaction support."""

    def __init__(
        self,
        gateway: MovieMetadataGateway,
        merge_gateway: MovieMergeGateway,
    ) -> None:
        self._gateway = gateway
        self._merge_gateway = merge_gateway

    async def get(self, movie_id: str) -> MovieMetadataSnapshot | None:
        """Read stable-ID state without inferring successful enrichment."""
        row = await self._gateway.get(movie_id)
        return self._snapshot(row) if row is not None else None

    async def find_by_tmdb_id(self, tmdb_id: str) -> MovieMetadataSnapshot | None:
        """Look up the supported TMDB identity, never a generic provider ID."""
        row = await self._gateway.find_by_tmdb_id(tmdb_id)
        return self._snapshot(row) if row is not None else None

    async def list_tmdb_movies(self) -> tuple[MovieMetadataSnapshot, ...]:
        """Include legacy known identities with no successful enrichment stamp."""
        return tuple(
            self._snapshot(row) for row in await self._gateway.list_tmdb_movies()
        )

    async def update_metadata(
        self,
        expected: MovieMetadataSnapshot,
        values: MovieMetadataValues,
        tmdb_id: str,
        enriched_at: datetime,
    ) -> MovieMetadataSnapshot:
        """Map a selected patch without adding eligibility or authority policy."""
        patch = asdict(values)
        for name in ("directors", "cast", "genres", "origin_countries"):
            if patch[name] is not None:
                patch[name] = ",".join(patch[name])
        patch["cast_members"] = patch.pop("cast")
        try:
            row = await self._gateway.update_metadata(
                expected.movie_id,
                expected.revision,
                patch,
                tmdb_id,
                enriched_at,
            )
        except MovieMetadataConflictError as exc:
            raise MovieWorkflowConflictError(str(exc)) from exc
        return self._snapshot(row)

    async def merge(self, request: MergeMoviesInputData) -> MergeMoviesOutputData:
        """Delegate to #356's injected implementation without a production stub."""
        return await self._merge_gateway.merge(request)

    @staticmethod
    def _snapshot(row: dict) -> MovieMetadataSnapshot:
        values = {
            name: row.get(name) for name in MovieMetadataValues.__dataclass_fields__
        }
        values["cast"] = row.get("cast_members")
        for name in ("directors", "cast", "genres", "origin_countries"):
            raw = values[name]
            values[name] = tuple(raw.split(",")) if raw is not None else None
        return MovieMetadataSnapshot(
            movie_id=row["id"],
            revision=row["revision"],
            values=MovieMetadataValues(**values),
            tmdb_id=row["tmdb_id"],
            metadata_enriched_at=row["metadata_enriched_at"],
            screening_ids=tuple(row["screening_ids"]),
        )
