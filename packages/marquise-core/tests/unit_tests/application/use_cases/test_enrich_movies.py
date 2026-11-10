"""Batch enrichment: which failures stop the batch, and which skip one movie."""

from datetime import UTC, datetime
from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.exceptions import (
    MetadataFailure,
    MetadataInvalidDataError,
    MetadataNotFoundError,
    MetadataRateLimitedError,
    MetadataUnavailableError,
    MovieMetadataUnavailableError,
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

    assert output == use_case.OutputData(enriched_ids=("one",), skipped_ids=())
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

    assert output == use_case.OutputData(enriched_ids=(), skipped_ids=())
    provider.movie_details.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_type", [MetadataUnavailableError, MetadataRateLimitedError]
)
async def test_outage_raises(
    use_case: EnrichMoviesUseCase,
    provider: Mock,
    failure_type: type[MetadataFailure],
) -> None:
    """TMDB being down stops the batch."""
    _fail_with(provider, failure_type)

    with pytest.raises(MovieMetadataUnavailableError):
        await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_type", [MetadataInvalidDataError, MetadataNotFoundError]
)
async def test_bad_data_skips_only_that_movie(
    use_case: EnrichMoviesUseCase,
    provider: Mock,
    failure_type: type[MetadataFailure],
) -> None:
    """Bad data for one movie is not an outage, so the batch carries on."""
    _fail_with(provider, failure_type)

    output = await use_case.execute(
        use_case.InputData((MovieInput("one", "7"), MovieInput("two", "8")))
    )

    assert output == use_case.OutputData(enriched_ids=(), skipped_ids=("one", "two"))


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
