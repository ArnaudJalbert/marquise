"""CLI composition for metadata refresh and guarded merge."""

import asyncio
import sys
from pathlib import Path

from marquise import create_factory_session
from marquise_cli.merge_movies import apply_merge, dry_run_merge, format_merge
from marquise_cli.refresh_command import run_refresh_movies


def refresh(movie_id: str | None, all_movies: bool) -> int:
    """Refresh a selected movie or every confirmed movie."""

    async def run() -> int:
        async with create_factory_session() as factory:
            return await run_refresh_movies(
                factory.movies.refresh_movies_use_case,
                movie_id=movie_id,
                all_movies=all_movies,
            )

    return asyncio.run(run())


def merge_preview(survivor_id: str, duplicate_ids: list[str]) -> int:
    """Print an exact preview for targeted movie IDs."""

    async def run() -> int:
        async with create_factory_session() as factory:
            result = await dry_run_merge(
                factory.movies.merge_movies_use_case, survivor_id, tuple(duplicate_ids)
            )
            print(format_merge(result, survivor_id, tuple(duplicate_ids)))
            return 0 if result.status == "preview" else 1

    return asyncio.run(run())


def merge_apply(survivor_id: str, duplicate_ids: list[str], preview_file: str) -> int:
    """Apply the explicit, previously generated preview."""
    try:
        preview = Path(preview_file).read_text()
    except OSError:
        print("Invalid or unreadable merge preview.", file=sys.stderr)
        return 2

    async def run() -> int:
        async with create_factory_session() as factory:
            result = await apply_merge(
                factory.movies.merge_movies_use_case,
                survivor_id,
                tuple(duplicate_ids),
                preview,
            )
            print(format_merge(result, survivor_id, tuple(duplicate_ids)))
            return 0 if result.status == "applied" else 1

    try:
        return asyncio.run(run())
    except (ValueError, KeyError):
        print("Invalid or unreadable merge preview.", file=sys.stderr)
        return 2
