"""Exercise matching and enrichment through the real import pipeline."""

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions.movie import MovieMetadataUnavailableError
from marquise.application.metadata import ProviderIdentity
from marquise.application.movie_workflows import (
    MovieMetadataRepository,
    MovieMetadataSnapshot,
    MovieMetadataValues,
)
from marquise.application.repositories import MovieRepository
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId
from support.movie_import import (
    Outcome,
    build_match,
    build_matcher,
    build_movie_import,
    build_unchanged_enricher,
)


def _movies() -> MovieRepository:
    movies = create_autospec(MovieRepository, instance=True)
    movies.find_by_tmdb_id.return_value = None
    movies.find_by_titles.return_value = []
    movies.create_or_reuse.side_effect = lambda movie: movie
    return movies


@pytest.mark.asyncio
async def test_mixed_matches_preserve_source_titles() -> None:
    """Matched and unmatched movies are both imported in one batch."""
    matcher = build_matcher(
        build_match("123"), Outcome("unmatched"), Outcome("incomplete")
    )
    enricher = build_unchanged_enricher()
    command = build_movie_import(_movies(), matcher, enricher)
    result = await command.execute(
        command.InputData(
            movies=(
                command.build_movie_input(
                    title="CINEMANIA: Julián",
                    identity_title="Julián",
                    release_year=2025,
                ),
                command.build_movie_input(title="Unmatched"),
                command.build_movie_input(title="Too Many Candidates"),
            )
        )
    )
    assert {movie.title for movie in result.movies} == {
        "CINEMANIA: Julián",
        "Unmatched",
        "Too Many Candidates",
    }
    request = matcher.execute.await_args.args[0]
    assert request.movies[0].identity_title == "Julián"
    enriched = enricher.execute.await_args.args[0].movies
    assert {movie.tmdb_id for movie in enriched} == {"123", None}


@pytest.mark.asyncio
async def test_failed_matching_stops_before_any_movie_is_created() -> None:
    """A TMDB outage raises instead of importing the movie by title alone."""
    movies = _movies()
    matcher = build_matcher()
    matcher.execute.side_effect = MovieMetadataUnavailableError("offline")
    command = build_movie_import(movies, matcher)
    with pytest.raises(MovieMetadataUnavailableError):
        await command.execute(
            command.InputData(movies=(command.build_movie_input(title="Offline"),))
        )
    movies.create_or_reuse.assert_not_awaited()


@pytest.mark.asyncio
async def test_remake_reusing_a_year_titled_row_keeps_the_source_title() -> None:
    """Screenings look movies up by source title, so a remake must still link."""
    movies = _movies()
    movies.find_by_titles.return_value = [
        Movie(id=MovieId(value="old"), title="Odyssey", tmdb_id="1"),
        Movie(id=MovieId(value="new"), title="Odyssey (2021)", release_year=2021),
    ]
    command = build_movie_import(movies, build_matcher(build_match("2")))
    result = await command.execute(
        command.InputData(
            movies=(command.build_movie_input(title="Odyssey", release_year=2021),)
        )
    )
    assert result.movies == (command.MovieData(title="Odyssey", id="new"),)


@pytest.mark.asyncio
async def test_same_title_distinct_identities_remain_separate() -> None:
    """Confirmed IDs with the same source title create different movies."""
    command = build_movie_import(
        _movies(), build_matcher(build_match("1"), build_match("2"))
    )
    result = await command.execute(
        command.InputData(
            movies=(
                command.build_movie_input(title="Same", source_identifier="one"),
                command.build_movie_input(title="Same", source_identifier="two"),
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
    from marquise.application.use_cases.enrich_movies import EnrichMoviesUseCase
    from marquise.application.use_cases.match_movies import MatchMoviesUseCase
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
    movies = _movies()
    metadata_movies = create_autospec(MovieMetadataRepository, instance=True)
    metadata_movies.get.side_effect = lambda movie_id: MovieMetadataSnapshot(
        movie_id, "1", MovieMetadataValues(title="CINEMANIA: Julián"), tmdb_id="123"
    )
    matcher = MatchMoviesUseCase(provider, RapidFuzzNameDistance())
    enricher = EnrichMoviesUseCase(
        metadata_movies, provider, lambda: datetime(2026, 10, 31, tzinfo=UTC)
    )
    command = build_movie_import(movies, matcher, enricher)
    result = await command.execute(
        command.InputData(
            movies=(
                command.build_movie_input(
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
