"""Metadata persistence maps the exact contract through autospecced gateways."""

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.movie_workflows import (
    MergeMoviesInputData,
    MergeMoviesOutputData,
    MovieMetadataSnapshot,
    MovieMetadataValues,
    MovieWorkflowConflictError,
)
from marquise.interface_adapters.repositories import (
    movie_metadata_repository,
)
from marquise.interface_adapters.repositories.protocols.movie_metadata import (
    MovieMergeGateway,
    MovieMetadataConflictError,
    MovieMetadataGateway,
)

PostgresMovieMetadataRepository = (
    movie_metadata_repository.PostgresMovieMetadataRepository
)


@pytest.mark.asyncio
async def test_snapshot_reads_include_legacy_pending_identities() -> None:
    """Explicit TMDB reads map legacy identity without inferring completion."""
    gateway = create_autospec(MovieMetadataGateway, instance=True)
    merge = create_autospec(MovieMergeGateway, instance=True)
    row = {
        "id": "movie",
        "revision": "revision",
        "title": "Source",
        "tmdb_id": "42",
        "metadata_enriched_at": None,
        "screening_ids": ["screening"],
        "directors": "A,B",
        "cast_members": "C,D",
        "genres": "Drama",
        "origin_countries": "CA",
    }
    gateway.get.return_value = row
    gateway.find_by_tmdb_id.return_value = row
    gateway.list_tmdb_movies.return_value = [row]
    repository = PostgresMovieMetadataRepository(gateway, merge)
    expected = MovieMetadataSnapshot(
        movie_id="movie",
        revision="revision",
        tmdb_id="42",
        screening_ids=("screening",),
        values=MovieMetadataValues(
            title="Source",
            directors=("A", "B"),
            cast=("C", "D"),
            genres=("Drama",),
            origin_countries=("CA",),
        ),
    )
    assert await repository.get("movie") == expected
    assert await repository.find_by_tmdb_id("42") == expected
    assert await repository.list_tmdb_movies() == (expected,)
    gateway.get.assert_awaited_once_with("movie")
    gateway.find_by_tmdb_id.assert_awaited_once_with("42")
    gateway.list_tmdb_movies.assert_awaited_once_with()
    merge.merge.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_snapshot_reads_return_none() -> None:
    """Missing movie and TMDB IDs stay absent instead of becoming empty snapshots."""
    gateway = create_autospec(MovieMetadataGateway, instance=True)
    gateway.get.return_value = gateway.find_by_tmdb_id.return_value = None
    gateway.list_tmdb_movies.return_value = []
    repository = PostgresMovieMetadataRepository(
        gateway,
        create_autospec(MovieMergeGateway, instance=True),
    )
    assert await repository.get("missing") is None
    assert await repository.find_by_tmdb_id("missing") is None
    assert await repository.list_tmdb_movies() == ()


@pytest.mark.asyncio
async def test_patch_mapping_keeps_none_and_passes_stable_id_revision() -> None:
    """Adapter serializes selected fields without adding eligibility policy."""
    gateway = create_autospec(MovieMetadataGateway, instance=True)
    stamp = datetime(2026, 10, 30, tzinfo=UTC)
    gateway.update_metadata.return_value = {
        "id": "movie",
        "revision": "new",
        "title": "Canonical",
        "tmdb_id": "42",
        "metadata_enriched_at": stamp,
        "screening_ids": [],
    }
    repository = PostgresMovieMetadataRepository(
        gateway,
        create_autospec(MovieMergeGateway, instance=True),
    )
    expected = MovieMetadataSnapshot("movie", "old", MovieMetadataValues())
    result = await repository.update_metadata(
        expected,
        MovieMetadataValues(title="Canonical", directors=("A", "B"), cast=()),
        "42",
        stamp,
    )
    gateway.update_metadata.assert_awaited_once()
    movie_id, revision, patch, identity, time = gateway.update_metadata.call_args.args
    assert (movie_id, revision, identity, time) == ("movie", "old", "42", stamp)
    assert patch == {
        "title": "Canonical",
        "original_title": None,
        "description": None,
        "release_year": None,
        "directors": "A,B",
        "cast_members": "",
        "duration_minutes": None,
        "genres": None,
        "origin_countries": None,
        "poster_url": None,
        "trailer_url": None,
        "rating": None,
        "tmdb_rating": None,
        "tmdb_vote_count": None,
    }
    assert result.revision == "new" and result.metadata_enriched_at == stamp


@pytest.mark.asyncio
async def test_conflict_translation_preserves_application_error_contract() -> None:
    """Stale and collision failures cross the adapter as the agreed error type."""
    gateway = create_autospec(MovieMetadataGateway, instance=True)
    gateway.update_metadata.side_effect = MovieMetadataConflictError("stale")
    repository = PostgresMovieMetadataRepository(
        gateway,
        create_autospec(MovieMergeGateway, instance=True),
    )
    with pytest.raises(MovieWorkflowConflictError, match="stale"):
        await repository.update_metadata(
            MovieMetadataSnapshot("movie", "old", MovieMetadataValues()),
            MovieMetadataValues(),
            "42",
            datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_merge_is_delegated_to_independent_transaction() -> None:
    """The adapter satisfies merge without implementing #356's transaction."""
    gateway = create_autospec(MovieMetadataGateway, instance=True)
    merge = create_autospec(MovieMergeGateway, instance=True)
    request = MergeMoviesInputData("survivor", ("duplicate",))
    result = MergeMoviesOutputData("blocked", (), blockers=("missing",))
    merge.merge.return_value = result
    repository = PostgresMovieMetadataRepository(gateway, merge)
    assert await repository.merge(request) is result
    merge.merge.assert_awaited_once_with(request)
    gateway.update_metadata.assert_not_awaited()


@pytest.mark.asyncio
async def test_legacy_empty_collection_strings_remain_missing() -> None:
    """Empty legacy collection strings retain the existing repository semantics."""
    gateway = create_autospec(MovieMetadataGateway, instance=True)
    gateway.get.return_value = {
        "id": "movie",
        "revision": "old",
        "title": "Legacy",
        "tmdb_id": "42",
        "metadata_enriched_at": None,
        "screening_ids": [],
        "directors": "",
        "cast_members": "",
        "genres": "",
        "origin_countries": "",
    }
    repository = PostgresMovieMetadataRepository(
        gateway,
        create_autospec(MovieMergeGateway, instance=True),
    )
    result = await repository.get("movie")
    assert result is not None
    assert result.values == MovieMetadataValues(title="Legacy")
