"""Merge policy uses shared facts and an autospecced matcher, without I/O."""

from dataclasses import replace
from unittest.mock import create_autospec

import pytest

from marquise.application.metadata import MetadataFailure, ProviderIdentity
from marquise.application.movie_workflows import (
    MatchMovieExecutor,
    MatchMovieOutputData,
    MergeMoviesInputData,
    MergeMoviesOutputData,
    MovieMetadataRepository,
    MovieMetadataSnapshot,
    MovieMetadataValues,
)
from marquise.application.use_cases.merge_movies import MergeMoviesUseCase


def snapshots() -> tuple[MovieMetadataSnapshot, ...]:
    """Supply distinct titles with one known canonical owner."""
    return tuple(
        MovieMetadataSnapshot(
            name,
            "revision-" + name,
            MovieMetadataValues(
                title=title,
                release_year=2026,
                directors=("Director",),
                duration_minutes=100,
            ),
            "1401459" if name == "a" else None,
            screening_ids=(name + "-screening",),
        )
        for name, title in [("a", "Fjord"), ("b", "Fjord VF"), ("c", "Fjord VO")]
    )


def collaborators() -> tuple:
    """Provide signature-checked collaborators with no concrete implementations."""
    repository = create_autospec(MovieMetadataRepository, instance=True)
    matcher = create_autospec(MatchMovieExecutor, instance=True)
    repository.merge.return_value = MergeMoviesOutputData("preview", snapshots())
    repository.find_by_tmdb_id.return_value = snapshots()[0]
    matcher.execute.return_value = MatchMovieOutputData(
        "matched", ProviderIdentity("tmdb", "1401459")
    )
    return repository, matcher, MergeMoviesUseCase(repository, matcher)


@pytest.mark.asyncio
async def test_preview_validates_every_movie_without_apply() -> None:
    """Fjord's three rows share confirmed identity; preview never submits approval."""
    repo, matcher, use_case = collaborators()
    result = await use_case.execute(MergeMoviesInputData("a", ("b", "c")))
    assert result.status == "preview"
    repo.merge.assert_awaited_once_with(MergeMoviesInputData("a", ("b", "c")))
    assert matcher.execute.await_count == 3
    assert matcher.execute.await_args_list[1].args[0].title == "Fjord VF"


@pytest.mark.asyncio
async def test_apply_passes_exact_approval_after_rematching() -> None:
    """Apply rechecks approved identity evidence and passes the original request."""
    repo, matcher, use_case = collaborators()
    repo.merge.side_effect = [
        MergeMoviesOutputData("preview", snapshots()),
        MergeMoviesOutputData("applied", snapshots(), ("b-screening", "c-screening")),
    ]
    request = MergeMoviesInputData("a", ("b", "c"), snapshots())
    assert (await use_case.execute(request)).status == "applied"
    assert repo.merge.await_args.args == (request,)
    assert matcher.execute.await_count == 3


@pytest.mark.parametrize("status", ["unmatched", "incomplete", "failed"])
@pytest.mark.asyncio
async def test_unconfirmed_evidence_blocks_apply(status: str) -> None:
    """A lookup failure or lack of confirmation cannot authorize a merge."""
    repo, matcher, use_case = collaborators()
    matcher.execute.return_value = MatchMovieOutputData(
        status,
        failure=MetadataFailure("unavailable", "offline")
        if status == "failed"
        else None,
    )
    result = await use_case.execute(MergeMoviesInputData("a", ("b", "c"), snapshots()))
    assert result.status == "blocked"
    repo.merge.assert_awaited_once()


@pytest.mark.parametrize(
    "change", ["conflict", "owner", "references", "duplicate_snapshot", "missing_title"]
)
@pytest.mark.asyncio
async def test_unsafe_plan_blocks(change: str) -> None:
    """Conflicting identity, wrong owner and invalid snapshots refuse writes."""
    repo, matcher, use_case = collaborators()
    approved = list(snapshots())
    if change == "conflict":
        matcher.execute.side_effect = [
            MatchMovieOutputData("matched", ProviderIdentity("tmdb", str(i)))
            for i in range(3)
        ]
    elif change == "owner":
        approved[1] = replace(approved[1], tmdb_id="1401459")
    elif change == "references":
        approved[1] = replace(approved[1], unresolved_references=("watchlist",))
    elif change == "duplicate_snapshot":
        approved.append(approved[0])
    else:
        approved[1] = replace(approved[1], values=MovieMetadataValues())
    result = await use_case.execute(
        MergeMoviesInputData("a", ("b", "c"), tuple(approved))
    )
    assert result.status == "blocked"
    repo.merge.assert_awaited_once()


@pytest.mark.asyncio
async def test_existing_owner_outside_targets_blocks() -> None:
    """A linked owner outside the requested group cannot be silently bypassed."""
    repo, _, use_case = collaborators()
    repo.find_by_tmdb_id.return_value = replace(snapshots()[0], movie_id="outside")
    assert (
        await use_case.execute(MergeMoviesInputData("a", ("b", "c")))
    ).status == "blocked"


@pytest.mark.parametrize("provider", ["tmdb", "another-provider"])
@pytest.mark.parametrize("stored_id", [None, "", "   "])
@pytest.mark.asyncio
async def test_unlinked_groups_refuse_without_persisted_identity(
    provider: str, stored_id: str | None
) -> None:
    """Unlinked groups refuse until approval can retain confirmed identity."""
    repo, matcher, use_case = collaborators()
    unlinked = tuple(replace(s, tmdb_id=stored_id) for s in snapshots())
    repo.merge.return_value = MergeMoviesOutputData("preview", unlinked)
    repo.find_by_tmdb_id.return_value = None
    matcher.execute.return_value = MatchMovieOutputData(
        "matched", ProviderIdentity(provider, "42")
    )
    assert (
        await use_case.execute(MergeMoviesInputData("a", ("b", "c")))
    ).status == "blocked"
