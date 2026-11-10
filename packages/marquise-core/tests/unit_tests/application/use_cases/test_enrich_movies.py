"""Batch enrichment: any failure leaves only that movie not enriched."""

from datetime import UTC, datetime
from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.exceptions import (
    MetadataFailure,
    MetadataInvalidDataError,
    MetadataNotFoundError,
    MetadataRateLimitedError,
    MetadataUnavailableError,
)
from marquise.application.metadata import (
    MetadataBatch,
    MetadataMovie,
    MetadataRepository,
    ProviderIdentity,
)
from marquise.application.movie_workflows import (
    MovieMetadataRepository,
    MovieMetadataSnapshot,
    MovieMetadataValues,
    MovieWorkflowConflictError,
)
from marquise.application.use_cases.enrich_movies import EnrichMoviesUseCase

MovieInput = EnrichMoviesUseCase.MovieInput


def _snapshot(movie_id: str, tmdb_id: str | None = None) -> MovieMetadataSnapshot:
    return MovieMetadataSnapshot(
        movie_id, "1", MovieMetadataValues(title="Film"), tmdb_id
    )


@pytest.fixture
def movie_repository() -> Mock:
    """Stored movies with no TMDB identity of their own."""
    movie_repository = create_autospec(MovieMetadataRepository, instance=True)
    movie_repository.get.side_effect = _snapshot
    return movie_repository


@pytest.fixture
def provider() -> Mock:
    """A provider that returns one complete detail per identity."""
    provider = create_autospec(MetadataRepository, instance=True)
    provider.movie_details.side_effect = lambda identity: MetadataBatch(
        (MetadataMovie(identity, ()),)
    )
    return provider


@pytest.fixture
def use_case(movie_repository: Mock, provider: Mock) -> EnrichMoviesUseCase:
    """The use case under test, with a fixed clock."""
    return EnrichMoviesUseCase(
        movie_repository, provider, lambda: datetime(2026, 10, 31, tzinfo=UTC)
    )


def _fail_with(provider: Mock, failure_type: type[MetadataFailure]) -> None:
    provider.movie_details.side_effect = lambda identity: MetadataBatch(
        (), complete=False, failure=failure_type("nope")
    )


@pytest.mark.asyncio
async def test_enriches_with_the_identity_from_matching(
    use_case: EnrichMoviesUseCase, provider: Mock
) -> None:
    """A confirmed identity is used, and the movie is reported as enriched."""
    output = await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))

    assert output == use_case.OutputData(enriched_ids=("one",), not_enriched_ids=())
    provider.movie_details.assert_awaited_once_with(ProviderIdentity("tmdb", "7"))


@pytest.mark.asyncio
async def test_falls_back_to_the_stored_identity(
    use_case: EnrichMoviesUseCase, movie_repository: Mock, provider: Mock
) -> None:
    """A title-matched row enriches from the TMDB ID it already has."""
    movie_repository.get.side_effect = lambda movie_id: _snapshot(movie_id, "9")

    await use_case.execute(use_case.InputData((MovieInput("one"),)))

    provider.movie_details.assert_awaited_once_with(ProviderIdentity("tmdb", "9"))


@pytest.mark.asyncio
async def test_movie_with_no_known_identity_is_left_out(
    use_case: EnrichMoviesUseCase, provider: Mock
) -> None:
    """No identity anywhere is an accepted outcome, reported as neither."""
    output = await use_case.execute(use_case.InputData((MovieInput("one"),)))

    assert output == use_case.OutputData(enriched_ids=(), not_enriched_ids=())
    provider.movie_details.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_type",
    [
        MetadataUnavailableError,
        MetadataRateLimitedError,
        MetadataInvalidDataError,
        MetadataNotFoundError,
    ],
)
async def test_failure_leaves_only_that_movie_not_enriched(
    use_case: EnrichMoviesUseCase,
    provider: Mock,
    failure_type: type[MetadataFailure],
) -> None:
    """An outage or bad data leaves the movie not enriched; the batch carries on."""
    _fail_with(provider, failure_type)

    output = await use_case.execute(
        use_case.InputData((MovieInput("one", "7"), MovieInput("two", "8")))
    )

    assert output == use_case.OutputData(
        enriched_ids=(), not_enriched_ids=("one", "two")
    )


@pytest.mark.asyncio
async def test_mismatched_detail_identity_leaves_the_movie_not_enriched(
    use_case: EnrichMoviesUseCase, provider: Mock
) -> None:
    """TMDB answering with a different record is bad data, not a bug."""
    provider.movie_details.side_effect = lambda identity: MetadataBatch(
        (MetadataMovie(ProviderIdentity("tmdb", "other"), ()),)
    )

    output = await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))

    assert output == use_case.OutputData(enriched_ids=(), not_enriched_ids=("one",))


@pytest.mark.asyncio
async def test_identity_conflict_leaves_the_movie_not_enriched(
    use_case: EnrichMoviesUseCase, movie_repository: Mock
) -> None:
    """A stored movie owned by another TMDB ID is left not enriched."""
    movie_repository.get.side_effect = lambda movie_id: _snapshot(movie_id, "9")

    output = await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))

    assert output == use_case.OutputData(enriched_ids=(), not_enriched_ids=("one",))


@pytest.mark.asyncio
async def test_unresolved_write_conflict_leaves_the_movie_not_enriched(
    use_case: EnrichMoviesUseCase, movie_repository: Mock
) -> None:
    """A write conflict that cannot be disambiguated leaves the movie as it is."""
    movie_repository.update_metadata.side_effect = MovieWorkflowConflictError("taken")

    output = await use_case.execute(
        use_case.InputData((MovieInput("one", "7"), MovieInput("two", "8")))
    )

    assert output == use_case.OutputData(
        enriched_ids=(), not_enriched_ids=("one", "two")
    )


@pytest.mark.asyncio
async def test_naive_clock_leaves_the_movie_not_enriched(
    movie_repository: Mock, provider: Mock
) -> None:
    """A bug in the injected clock leaves the movie not enriched, never written."""
    use_case = EnrichMoviesUseCase(
        movie_repository, provider, lambda: datetime(2026, 10, 31)
    )

    output = await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))

    assert output == use_case.OutputData(enriched_ids=(), not_enriched_ids=("one",))
    movie_repository.update_metadata.assert_not_awaited()


@pytest.mark.parametrize("fields", [{"movie_id": 1}, {"movie_id": "one", "tmdb_id": 7}])
def test_movie_input_rejects_wrong_types(fields: dict) -> None:
    """Input is the one place types are checked."""
    with pytest.raises(TypeError):
        MovieInput(**fields)


@pytest.mark.parametrize("movies", [["one"], ("one",)])
def test_input_rejects_wrong_types(movies: object) -> None:
    """The batch must be a tuple of movie inputs."""
    with pytest.raises(TypeError):
        EnrichMoviesUseCase.InputData(movies=movies)
