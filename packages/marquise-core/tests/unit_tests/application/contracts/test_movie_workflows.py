"""Validation and source-state contracts for movie workflows."""

import pytest

from marquise import (
    EnrichMovieOutputData,
    MergeMoviesInputData,
    MetadataRateLimitedError,
    MovieMetadataSnapshot,
    MovieMetadataValues,
    ProviderIdentity,
)
from marquise.application.metadata import (
    MetadataBatch,
)
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


def test_partial_batch_preserves_facts() -> None:
    """A failed later page retains ordered earlier facts but cannot be complete."""
    failure = MetadataRateLimitedError("Later page failed")
    assert MetadataBatch(("first",), False, failure).items == ("first",)
    with pytest.raises(ValueError, match="incomplete"):
        MetadataBatch(failure=failure)


@pytest.mark.parametrize("provider,identifier", [("", "1"), ("tmdb", " ")])
def test_identity_scope_required(provider: str, identifier: str) -> None:
    """Opaque IDs cannot lose the provider label."""
    with pytest.raises(ValueError, match="nonempty"):
        ProviderIdentity(provider, identifier)


def test_enrichment_outcomes() -> None:
    """A movie left not enriched always carries its failure."""
    with pytest.raises(ValueError):
        EnrichMovieOutputData("1", "not_enriched")


def test_stable_id_persistence_contract() -> None:
    """Source movie identity does not imply successful enrichment."""
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
