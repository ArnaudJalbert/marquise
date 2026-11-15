"""Batch enrichment skips expected misses and propagates other failures."""

import logging
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
    TitleFact,
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
    [MetadataInvalidDataError, MetadataNotFoundError],
)
async def test_expected_miss_skips_only_that_movie_and_continues(
    use_case: EnrichMoviesUseCase,
    provider: Mock,
    failure_type: type[MetadataFailure],
) -> None:
    """A missing or invalid detail skips one Movie while the next enriches."""
    failure = failure_type("nope")
    miss = MetadataBatch((), complete=False, failure=failure)
    success = MetadataBatch((MetadataMovie(ProviderIdentity("tmdb", "8"), ()),))
    provider.movie_details.side_effect = [miss, success]

    output = await use_case.execute(
        use_case.InputData((MovieInput("one", "7"), MovieInput("two", "8")))
    )

    assert output == use_case.OutputData(
        enriched_ids=("two",), not_enriched_ids=("one",)
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_type", [MetadataUnavailableError, MetadataRateLimitedError]
)
async def test_metadata_outage_stops_enrichment(
    use_case: EnrichMoviesUseCase,
    provider: Mock,
    failure_type: type[MetadataFailure],
) -> None:
    """An outage propagates unchanged and stops before the next Movie."""
    failure = failure_type("provider down")
    batch = MetadataBatch((), complete=False, failure=failure)
    provider.movie_details.side_effect = [batch]
    with pytest.raises(failure_type) as raised:
        await use_case.execute(
            use_case.InputData((MovieInput("one", "7"), MovieInput("two", "8")))
        )
    assert raised.value is failure
    provider.movie_details.assert_awaited_once()


@pytest.mark.asyncio
async def test_partial_batch_outage_stops_before_writing(
    use_case: EnrichMoviesUseCase, movie_repository: Mock, provider: Mock
) -> None:
    """An outage with usable partial detail propagates without persisting it."""
    failure = MetadataUnavailableError("Partial")
    provider.movie_details.side_effect = None
    provider.movie_details.return_value = MetadataBatch(
        (MetadataMovie(ProviderIdentity("tmdb", "7"), ()),),
        complete=False,
        failure=failure,
    )
    with pytest.raises(MetadataUnavailableError) as raised:
        await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))
    assert raised.value is failure
    movie_repository.update_metadata.assert_not_awaited()


@pytest.mark.asyncio
async def test_unexpected_provider_error_propagates(
    use_case: EnrichMoviesUseCase, provider: Mock
) -> None:
    """An unexpected provider bug fails the run instead of becoming a miss."""
    provider.movie_details.side_effect = RuntimeError("provider bug")
    with pytest.raises(RuntimeError, match="provider bug"):
        await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))


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
async def test_identity_conflict_propagates(
    use_case: EnrichMoviesUseCase, movie_repository: Mock
) -> None:
    """A conflicting stored identity fails the run."""
    movie_repository.get.side_effect = lambda movie_id: _snapshot(movie_id, "9")

    with pytest.raises(MovieWorkflowConflictError):
        await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))


@pytest.mark.asyncio
async def test_unresolved_write_conflict_propagates(
    use_case: EnrichMoviesUseCase, movie_repository: Mock
) -> None:
    """A write conflict that cannot be disambiguated fails the run."""
    movie_repository.update_metadata.side_effect = MovieWorkflowConflictError("taken")

    with pytest.raises(MovieWorkflowConflictError, match="taken"):
        await use_case.execute(
            use_case.InputData((MovieInput("one", "7"), MovieInput("two", "8")))
        )


@pytest.mark.asyncio
async def test_naive_clock_propagates(movie_repository: Mock, provider: Mock) -> None:
    """A bug in the injected clock fails the run before writing."""
    use_case = EnrichMoviesUseCase(
        movie_repository, provider, lambda: datetime(2026, 10, 31)
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))
    movie_repository.update_metadata.assert_not_awaited()


@pytest.mark.asyncio
async def test_title_conflict_stores_year_and_warns(
    use_case: EnrichMoviesUseCase,
    movie_repository: Mock,
    provider: Mock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A remake keeps its year suffix and names the Movie and conflicting title."""
    provider.movie_details.side_effect = None
    provider.movie_details.return_value = MetadataBatch(
        (
            MetadataMovie(
                ProviderIdentity("tmdb", "7"),
                (TitleFact("Dune", "canonical", "en-US"),),
                release_year=2021,
            ),
        )
    )
    movie_repository.update_metadata.side_effect = [
        MovieWorkflowConflictError("title taken"),
        None,
    ]
    with caplog.at_level(logging.WARNING):
        output = await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))
    assert output == use_case.OutputData(enriched_ids=("one",), not_enriched_ids=())
    assert (
        movie_repository.update_metadata.await_args_list[-1].args[1].title
        == "Dune (2021)"
    )
    assert any(
        record.levelno == logging.WARNING
        and "one" in record.message
        and "Dune" in record.message
        for record in caplog.records
    )


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
