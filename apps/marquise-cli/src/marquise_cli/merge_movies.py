"""Thin targeted merge handlers. Factory and command registration belong to #355."""

import json
from dataclasses import asdict
from datetime import datetime

from marquise import (
    MergeMoviesExecutor,
    MergeMoviesInputData,
    MergeMoviesOutputData,
    MovieMetadataSnapshot,
    MovieMetadataValues,
)


def format_merge(
    result: MergeMoviesOutputData, survivor_id: str, duplicate_ids: tuple[str, ...]
) -> str:
    """Render exact approval evidence, references, screening IDs and counts."""
    data = asdict(result)
    data["survivor_id"] = survivor_id
    data["duplicate_ids"] = duplicate_ids
    data["screening_counts"] = {
        snap.movie_id: len(snap.screening_ids) for snap in result.snapshots
    }
    return json.dumps(data, default=lambda value: value.isoformat(), indent=2)


async def dry_run_merge(
    executor: MergeMoviesExecutor, survivor_id: str, duplicate_ids: tuple[str, ...]
) -> MergeMoviesOutputData:
    """Request a read-only preview for exactly these targets."""
    return await executor.execute(MergeMoviesInputData(survivor_id, duplicate_ids))


def _read_snapshot(data: dict) -> MovieMetadataSnapshot:
    values = dict(data["values"])
    for name in ("directors", "cast", "genres", "origin_countries"):
        if values.get(name) is not None:
            values[name] = tuple(values[name])
    return MovieMetadataSnapshot(
        movie_id=data["movie_id"],
        revision=data["revision"],
        values=MovieMetadataValues(**values),
        tmdb_id=data["tmdb_id"],
        metadata_enriched_at=(
            datetime.fromisoformat(data["metadata_enriched_at"])
            if data["metadata_enriched_at"]
            else None
        ),
        screening_ids=tuple(data["screening_ids"]),
        unresolved_references=tuple(data["unresolved_references"]),
    )


async def apply_merge(
    executor: MergeMoviesExecutor,
    survivor_id: str,
    duplicate_ids: tuple[str, ...],
    approved_preview: str,
) -> MergeMoviesOutputData:
    """Apply an explicitly supplied preview, never generate implicit approval."""
    data = json.loads(approved_preview)
    if (
        data["status"] != "preview"
        or data["blockers"]
        or data["survivor_id"] != survivor_id
        or data["duplicate_ids"] != list(duplicate_ids)
    ):
        raise ValueError("Approval requires an unblocked dry-run preview")
    snapshots = tuple(_read_snapshot(item) for item in data["snapshots"])
    return await executor.execute(
        MergeMoviesInputData(survivor_id, duplicate_ids, snapshots)
    )
