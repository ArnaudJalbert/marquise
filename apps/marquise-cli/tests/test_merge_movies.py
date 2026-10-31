"""Merge handlers keep approval explicit and use only the public facade."""

from datetime import datetime, timezone
from unittest.mock import create_autospec

import pytest

from marquise import (
    MergeMoviesExecutor,
    MergeMoviesInputData,
    MergeMoviesOutputData,
    MovieMetadataSnapshot,
    MovieMetadataValues,
    ProviderIdentity,
)
from marquise_cli.merge_movies import apply_merge, dry_run_merge, format_merge


@pytest.mark.asyncio
async def test_preview_and_exact_approval_roundtrip() -> None:
    """Formatting preserves every approved field including tuples and timestamps."""
    executor = create_autospec(MergeMoviesExecutor, instance=True)
    snapshots = tuple(
        MovieMetadataSnapshot(
            name,
            "revision",
            MovieMetadataValues(title=name, directors=("A", "B")),
            metadata_enriched_at=datetime(2026, 10, 30, tzinfo=timezone.utc),
            screening_ids=(name + "-screening",),
        )
        for name in ("survivor", "duplicate")
    )
    executor.execute.return_value = MergeMoviesOutputData(
        "preview", snapshots, confirmed_identity=ProviderIdentity("tmdb", "42")
    )
    preview = await dry_run_merge(executor, "survivor", ("duplicate",))
    executor.execute.assert_awaited_once_with(
        MergeMoviesInputData("survivor", ("duplicate",))
    )
    text = format_merge(preview, "survivor", ("duplicate",))
    assert "screening_counts" in text and "duplicate-screening" in text
    await apply_merge(executor, "survivor", ("duplicate",), text)
    assert executor.execute.await_args.args == (
        MergeMoviesInputData(
            "survivor", ("duplicate",), snapshots, ProviderIdentity("tmdb", "42")
        ),
    )


@pytest.mark.parametrize("status", ["blocked", "applied"])
@pytest.mark.asyncio
async def test_only_clean_preview_is_approval(status: str) -> None:
    """Blocked or previously applied output is never converted to fresh approval."""
    executor = create_autospec(MergeMoviesExecutor, instance=True)
    with pytest.raises(ValueError):
        await apply_merge(
            executor,
            "a",
            ("b",),
            format_merge(MergeMoviesOutputData(status, ()), "a", ("b",)),
        )
    executor.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_changed_target_set_is_rejected() -> None:
    """Approval cannot silently broaden a targeted merge."""
    executor = create_autospec(MergeMoviesExecutor, instance=True)
    with pytest.raises(ValueError):
        await apply_merge(
            executor,
            "a",
            ("b",),
            format_merge(MergeMoviesOutputData("preview", ()), "a", ("b",)),
        )
    executor.execute.assert_not_awaited()
