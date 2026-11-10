"""Small reusable autospec examples for downstream contract consumers."""

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise import (
    EnrichMovieOutputData,
    MergeMoviesExecutor,
    MergeMoviesInputData,
    MergeMoviesOutputData,
    MetadataBatch,
    MetadataMovie,
    MetadataNotFoundError,
    MetadataRateLimitedError,
    MetadataRepository,
    MovieMetadataRepository,
    MovieMetadataSnapshot,
    MovieMetadataValues,
    ProviderIdentity,
    RefreshMoviesExecutor,
    RefreshMoviesInputData,
    RefreshMoviesOutputData,
    TitleFact,
)
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


@pytest.fixture
def metadata_repository() -> MetadataRepository:
    """An independent provider seam with exhaustive empty discovery by default."""
    repository = create_autospec(MetadataRepository, instance=True, spec_set=True)
    repository.search_movies.return_value = MetadataBatch()
    repository.search_people.return_value = MetadataBatch()
    repository.directed_movies.return_value = MetadataBatch()
    repository.movie_details.return_value = MetadataBatch(
        complete=False, failure=MetadataNotFoundError("Missing movie")
    )
    return repository


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["tmdb", "independent-fixture"])
async def test_ordered_provider_facts(provider: str) -> None:
    """Identical facts support either provider without changing order or IDs."""
    repository = create_autospec(MetadataRepository, instance=True, spec_set=True)
    identity = ProviderIdentity(provider, "7340")
    movie = MetadataMovie(identity, (TitleFact("Carrie", "canonical"),), 1976)
    repository.search_movies.return_value = MetadataBatch((movie,))
    result = await repository.search_movies("Carrie", 1976)
    assert result.items == (movie,)
    repository.search_movies.assert_awaited_once_with("Carrie", 1976)


@pytest.mark.asyncio
async def test_empty_and_failed_retrieval(
    metadata_repository: MetadataRepository,
) -> None:
    """Exhaustive absence is distinct from a failed detail retrieval."""
    empty = await metadata_repository.search_movies("Unknown")
    failed = await metadata_repository.movie_details(ProviderIdentity("tmdb", "0"))
    assert empty.complete and empty.failure is None and empty.items == ()
    assert not failed.complete and isinstance(failed.failure, MetadataNotFoundError)


def test_partial_batch_preserves_facts() -> None:
    """A failed later page retains ordered earlier facts but cannot be complete."""
    failure = MetadataRateLimitedError("Later page failed", True)
    assert MetadataBatch(("first",), False, failure).items == ("first",)
    with pytest.raises(ValueError, match="incomplete"):
        MetadataBatch(failure=failure)


@pytest.mark.parametrize("provider,identifier", [("", "1"), ("tmdb", " ")])
def test_identity_scope_required(provider: str, identifier: str) -> None:
    """Opaque IDs cannot lose the provider label."""
    with pytest.raises(ValueError, match="nonempty"):
        ProviderIdentity(provider, identifier)


def test_enrichment_outcomes() -> None:
    """A failed enrichment always carries its failure."""
    with pytest.raises(ValueError):
        EnrichMovieOutputData("1", "failed")


@pytest.mark.asyncio
async def test_delivery_execution_seams() -> None:
    """Thin callers use only facade DTOs and autospecced execute signatures."""
    outcome = EnrichMovieOutputData("stable-id", "enriched")
    refresh = create_autospec(RefreshMoviesExecutor, instance=True, spec_set=True)
    refresh.execute.return_value = RefreshMoviesOutputData((outcome,))
    assert (await refresh.execute(RefreshMoviesInputData())).results == (outcome,)
    merger = create_autospec(MergeMoviesExecutor, instance=True, spec_set=True)
    merger.execute.return_value = MergeMoviesOutputData("preview", ())
    assert (await merger.execute(MergeMoviesInputData("keep", ("other",)))).status == (
        "preview"
    )
    with pytest.raises(TypeError):
        refresh.execute(RefreshMoviesInputData(), "extra")


@pytest.mark.asyncio
async def test_stable_id_persistence_contract() -> None:
    """Updates carry expected revisions and stamp successful enrichment separately."""
    repository = create_autospec(MovieMetadataRepository, instance=True, spec_set=True)
    before = MovieMetadataSnapshot("stable", "v1", MovieMetadataValues(title="Source"))
    now = datetime.now(UTC)
    patch = MovieMetadataValues(title="Canonical")
    after = MovieMetadataSnapshot("stable", "v2", patch, "7340", now)
    repository.update_metadata.return_value = after
    assert await repository.update_metadata(before, patch, "7340", now) == after
    repository.update_metadata.assert_awaited_once_with(before, patch, "7340", now)
    movie = Movie(id=MovieId("stable"), title="Source", tmdb_id="7340")
    assert movie.metadata_enriched_at is None


def test_merge_requires_targeted_snapshot() -> None:
    """A dry run has no approval and an apply request covers the exact targets."""
    keep = MovieMetadataSnapshot("keep", "v1", MovieMetadataValues(), "7340")
    other = MovieMetadataSnapshot("other", "v2", MovieMetadataValues())
    assert MergeMoviesInputData("keep", ("other",)).approved_snapshot is None
    approved = MergeMoviesInputData("keep", ("other",), (keep, other))
    assert approved.approved_snapshot == (keep, other)
    for duplicates in [(), ("keep",), ("other", "other")]:
        with pytest.raises(ValueError):
            MergeMoviesInputData("keep", duplicates)
    with pytest.raises(ValueError, match="exactly"):
        MergeMoviesInputData("keep", ("other",), (keep,))


def test_blank_workflow_inputs_are_rejected() -> None:
    """Matching and single-movie operations reject blank identifiers."""
    import pytest

    from marquise.application.metadata import ProviderIdentity
    from marquise.application.movie_workflows import (
        EnrichMovieInputData,
        RefreshMoviesInputData,
    )

    with pytest.raises(ValueError):
        EnrichMovieInputData(" ", ProviderIdentity("tmdb", "1"))
    with pytest.raises(ValueError):
        RefreshMoviesInputData(" ")
