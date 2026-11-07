"""Batch enrichment: which failures stop the batch, and which skip one movie."""

from datetime import UTC, datetime
from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.exceptions.movie import MovieMetadataUnavailableError
from marquise.application.metadata import (
    MetadataBatch,
    MetadataFailure,
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


def _movies() -> Mock:
    movies = create_autospec(MovieMetadataRepository, instance=True)
    movies.get.side_effect = _snapshot
    return movies


def _provider(failure: MetadataFailure | None = None) -> Mock:
    provider = create_autospec(MetadataRepository, instance=True)
    provider.movie_details.side_effect = lambda identity: (
        MetadataBatch((), complete=False, failure=failure)
        if failure
        else MetadataBatch((MetadataMovie(identity, ()),))
    )
    return provider


def _use_case(movies: Mock, provider: Mock) -> EnrichMoviesUseCase:
    return EnrichMoviesUseCase(
        movies, provider, lambda: datetime(2026, 10, 31, tzinfo=UTC)
    )


@pytest.mark.asyncio
async def test_enriches_with_the_identity_from_matching() -> None:
    """A confirmed identity is used and reported as enriched."""
    provider = _provider()
    use_case = _use_case(_movies(), provider)

    output = await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))

    assert output.results == (use_case.MovieResult("one", "enriched"),)
    provider.movie_details.assert_awaited_once_with(ProviderIdentity("tmdb", "7"))


@pytest.mark.asyncio
async def test_falls_to_the_stored_identity_when_matching_found_none() -> None:
    """A title-matched row enriches from the TMDB ID it already has."""
    movies = _movies()
    movies.get.side_effect = lambda movie_id: _snapshot(movie_id, "9")
    provider = _provider()
    use_case = _use_case(movies, provider)

    await use_case.execute(use_case.InputData((MovieInput("one"),)))

    provider.movie_details.assert_awaited_once_with(ProviderIdentity("tmdb", "9"))


@pytest.mark.asyncio
async def test_movie_with_no_known_identity_is_unchanged() -> None:
    """No identity anywhere is an accepted outcome."""
    provider = _provider()
    use_case = _use_case(_movies(), provider)

    output = await use_case.execute(use_case.InputData((MovieInput("one"),)))

    assert output.results == (use_case.MovieResult("one", "unchanged"),)
    provider.movie_details.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["unavailable", "rate_limited"])
async def test_outage_raises(kind: str) -> None:
    """TMDB being down stops the batch."""
    use_case = _use_case(_movies(), _provider(MetadataFailure(kind, "nope")))

    with pytest.raises(MovieMetadataUnavailableError):
        await use_case.execute(use_case.InputData((MovieInput("one", "7"),)))


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["invalid_data", "not_found"])
async def test_bad_data_skips_only_that_movie(kind: str) -> None:
    """Bad data for one movie is not an outage, so the batch carries on."""
    use_case = _use_case(_movies(), _provider(MetadataFailure(kind, "nope")))

    output = await use_case.execute(
        use_case.InputData((MovieInput("one", "7"), MovieInput("two", "8")))
    )

    assert output.results == (
        use_case.MovieResult("one", "skipped"),
        use_case.MovieResult("two", "skipped"),
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
