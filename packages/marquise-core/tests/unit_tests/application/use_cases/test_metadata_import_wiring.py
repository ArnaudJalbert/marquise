"""Exercise matching and enrichment while keeping imports available."""

from unittest.mock import create_autospec

import pytest

from marquise.application.metadata import MetadataFailure, ProviderIdentity
from marquise.application.movie_workflows import (
    EnrichMovieExecutor,
    EnrichMovieOutputData,
    MatchMovieExecutor,
    MatchMovieOutputData,
    MovieMetadataRepository,
)
from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)


@pytest.mark.asyncio
async def test_mixed_matches_preserve_source_titles_and_continue_on_failure() -> None:
    """Matched, unmatched and unavailable movies remain importable in one batch."""
    movies = create_autospec(MovieRepository, instance=True)
    movies.find_by_tmdb_id.return_value = None
    movies.find_by_titles.return_value = []
    movies.create_or_reuse.side_effect = lambda movie: movie
    metadata_movies = create_autospec(MovieMetadataRepository, instance=True)
    metadata_movies.get.return_value = None
    matcher = create_autospec(MatchMovieExecutor, instance=True)
    matcher.execute.side_effect = [
        MatchMovieOutputData("matched", ProviderIdentity("tmdb", "123")),
        MatchMovieOutputData("unmatched"),
        MatchMovieOutputData(
            "failed", failure=MetadataFailure("unavailable", "offline")
        ),
    ]
    enricher = create_autospec(EnrichMovieExecutor, instance=True)
    enricher.execute.side_effect = lambda request: EnrichMovieOutputData(
        request.movie_id, "enriched"
    )
    command = CreateMissingMoviesCommand(
        movies, matcher=matcher, enricher=enricher, metadata_movies=metadata_movies
    )
    result = await command.execute(
        command.InputData(
            movies=(
                command.MovieInput(
                    title="CINEMANIA: Julián",
                    identity_title="Julián",
                    release_year=2025,
                ),
                command.MovieInput(title="Unmatched"),
                command.MovieInput(title="Offline"),
            )
        )
    )
    assert {movie.title for movie in result.movies} == {
        "CINEMANIA: Julián",
        "Unmatched",
        "Offline",
    }
    assert matcher.execute.await_args_list[0].args[0].identity_title == "Julián"
    assert enricher.execute.await_count == 1
    assert enricher.execute.await_args.args[0].identity == ProviderIdentity(
        "tmdb", "123"
    )


@pytest.mark.asyncio
async def test_known_identity_stays_retryable_when_matching_is_unavailable() -> None:
    """A provider failure keeps the source import and retries known metadata."""
    from marquise.application.movie_workflows import (
        MovieMetadataSnapshot,
        MovieMetadataValues,
    )
    from marquise.domain.entities import Movie
    from marquise.domain.value_objects import MovieId

    repo = create_autospec(MovieRepository, instance=True)
    repo.find_by_titles.return_value = [
        Movie(id=MovieId(value="existing"), title="Existing", tmdb_id="123")
    ]
    metadata = create_autospec(MovieMetadataRepository, instance=True)
    metadata.get.return_value = MovieMetadataSnapshot(
        movie_id="existing",
        revision="1",
        values=MovieMetadataValues(title="Existing"),
        tmdb_id="123",
    )
    matcher = create_autospec(MatchMovieExecutor, instance=True)
    matcher.execute.return_value = MatchMovieOutputData(
        "failed", failure=MetadataFailure("unavailable", "offline")
    )
    enricher = create_autospec(EnrichMovieExecutor, instance=True)
    enricher.execute.return_value = EnrichMovieOutputData(
        "existing", "failed", MetadataFailure("unavailable", "offline")
    )
    command = CreateMissingMoviesCommand(
        repo, matcher=matcher, enricher=enricher, metadata_movies=metadata
    )
    result = await command.execute(
        command.InputData(movies=(command.MovieInput(title="Existing"),))
    )
    assert result.movies == (command.MovieData(title="Existing", id="existing"),)
    assert enricher.execute.await_args.args[0].identity == ProviderIdentity(
        "tmdb", "123"
    )
    repo.create_or_reuse.assert_not_awaited()


@pytest.mark.asyncio
async def test_same_title_distinct_identities_remain_separate() -> None:
    """Confirmed IDs with the same source title create different movies."""
    repo = create_autospec(MovieRepository, instance=True)
    repo.find_by_tmdb_id.return_value = None
    repo.find_by_titles.return_value = []
    repo.create_or_reuse.side_effect = lambda movie: movie
    matcher = create_autospec(MatchMovieExecutor, instance=True)
    matcher.execute.side_effect = [
        MatchMovieOutputData("matched", ProviderIdentity("tmdb", "1")),
        MatchMovieOutputData("matched", ProviderIdentity("tmdb", "2")),
    ]
    command = CreateMissingMoviesCommand(repo, matcher=matcher)
    result = await command.execute(
        command.InputData(
            movies=(
                command.MovieInput(title="Same", source_identifier="one"),
                command.MovieInput(title="Same", source_identifier="two"),
            )
        )
    )
    assert len({movie.id for movie in result.movies}) == 2
    assert {movie.source_identifier for movie in result.movies} == {"one", "two"}


@pytest.mark.asyncio
async def test_real_matcher_and_enricher_capture_selected_source_movie() -> None:
    """Real matching and enrichment cooperate through injected repositories."""
    from datetime import UTC, datetime

    from marquise.application.metadata import (
        LocalizedMovieMetadata,
        MetadataBatch,
        MetadataMovie,
        MetadataRepository,
        TitleFact,
    )
    from marquise.application.movie_workflows import (
        MovieMetadataSnapshot,
        MovieMetadataValues,
    )
    from marquise.application.use_cases.enrich_movie import EnrichMovieUseCase
    from marquise.application.use_cases.match_movie import MatchMovieUseCase
    from marquise.infrastructure.name_distance import RapidFuzzNameDistance

    identity = ProviderIdentity("tmdb", "123")
    candidate = MetadataMovie(
        identity,
        (TitleFact("Julián", "canonical"),),
        release_year=2025,
        duration_minutes=85,
        localized=(LocalizedMovieMetadata("fr-CA", title="Julián"),),
    )
    provider = create_autospec(MetadataRepository, instance=True)
    provider.search_movies.return_value = MetadataBatch((candidate,))
    provider.movie_details.return_value = MetadataBatch((candidate,))
    movies = create_autospec(MovieRepository, instance=True)
    movies.find_by_tmdb_id.return_value = None
    movies.find_by_titles.return_value = []
    movies.create_or_reuse.side_effect = lambda movie: movie
    metadata_movies = create_autospec(MovieMetadataRepository, instance=True)
    metadata_movies.get.side_effect = lambda movie_id: MovieMetadataSnapshot(
        movie_id, "1", MovieMetadataValues(title="CINEMANIA: Julián"), tmdb_id="123"
    )
    matcher = MatchMovieUseCase(provider, RapidFuzzNameDistance())
    enricher = EnrichMovieUseCase(
        metadata_movies, provider, lambda: datetime(2026, 10, 31, tzinfo=UTC)
    )
    command = CreateMissingMoviesCommand(
        movies, matcher=matcher, enricher=enricher, metadata_movies=metadata_movies
    )
    result = await command.execute(
        command.InputData(
            movies=(
                command.MovieInput(
                    title="CINEMANIA: Julián",
                    identity_title="Julián",
                    release_year=2025,
                    duration_minutes=85,
                ),
            )
        )
    )
    assert result.movies[0].title == "CINEMANIA: Julián"
    assert metadata_movies.update_metadata.await_count == 1
    assert metadata_movies.update_metadata.await_args.args[2] == "123"
