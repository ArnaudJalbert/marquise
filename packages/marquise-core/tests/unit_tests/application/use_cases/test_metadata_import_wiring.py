"""Exercise matching and enrichment through the real import pipeline."""

from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    MetadataDetailMappingError,
    MetadataFailure,
    MetadataInvalidDataError,
    MetadataNotFoundError,
    MetadataRateLimitedError,
    MetadataRequestRefusedError,
    MetadataUnavailableError,
    MovieMetadataUnavailableError,
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
)
from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.match_movies import MatchMoviesUseCase
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId
from support.movie_import import (
    MovieImport,
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
    matcher = MatchMoviesUseCase(provider)
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


def _tmdb_movie(tmdb_id: str, title: str) -> MetadataMovie:
    """Build one complete TMDB candidate."""
    return MetadataMovie(
        ProviderIdentity("tmdb", tmdb_id),
        (TitleFact(title, "canonical"),),
        release_year=2026,
        duration_minutes=100,
    )


def _fake_tmdb(
    results: dict[str, tuple[MetadataMovie, ...]],
    bad: dict[str, MetadataFailure],
) -> MetadataRepository:
    """A TMDB source with canned searches and failing details for some IDs."""
    known = {item.identity: item for items in results.values() for item in items}
    provider = create_autospec(MetadataRepository, instance=True)
    provider.search_movies.side_effect = lambda title, year=None: MetadataBatch(
        results.get(title, ())
    )
    provider.search_people.return_value = MetadataBatch()
    provider.directed_movies.return_value = MetadataBatch()

    def details(identity: ProviderIdentity) -> MetadataBatch[MetadataMovie]:
        if identity.id in bad:
            return MetadataBatch(complete=False, failure=bad[identity.id])
        return MetadataBatch((known[identity],))

    provider.movie_details.side_effect = details
    return provider


async def _import_with_tmdb(
    movies: MovieRepository, provider: MetadataRepository, *titles: str
) -> MovieImport.OutputData:
    """Import the titles through the real matcher and the given TMDB source."""
    matcher = MatchMoviesUseCase(provider)
    command = build_movie_import(movies, matcher)
    return await command.execute(
        command.InputData(
            movies=tuple(
                command.build_movie_input(
                    title=title, release_year=2026, duration_minutes=100
                )
                for title in titles
            )
        )
    )


def _created_tmdb_ids(movies: MovieRepository) -> dict[str, str | None]:
    """Map each created movie title to the TMDB ID it was saved with."""
    return {
        call.args[0].title: call.args[0].tmdb_id
        for call in movies.create_or_reuse.await_args_list
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_type", [MetadataInvalidDataError, MetadataNotFoundError]
)
async def test_bad_tmdb_data_skips_only_that_movie(
    failure_type: type[MetadataFailure],
) -> None:
    """One movie with bad TMDB data is left unmatched and the rest still import."""
    provider = _fake_tmdb(
        {"Bad": (_tmdb_movie("1", "Bad"),), "Good": (_tmdb_movie("2", "Good"),)},
        {"1": failure_type("bad")},
    )
    movies = _movies()
    await _import_with_tmdb(movies, provider, "Bad", "Good")
    assert _created_tmdb_ids(movies) == {"Bad": None, "Good": "2"}


@pytest.mark.asyncio
async def test_bad_tmdb_candidate_does_not_block_the_clear_match() -> None:
    """A bad candidate in a title search is set aside and the clear match wins."""
    provider = _fake_tmdb(
        {"Film": (_tmdb_movie("1", "Film"), _tmdb_movie("2", "Film"))},
        {"1": MetadataInvalidDataError("bad")},
    )
    movies = _movies()
    await _import_with_tmdb(movies, provider, "Film")
    assert _created_tmdb_ids(movies) == {"Film": "2"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_type",
    [MetadataUnavailableError, MetadataRequestRefusedError, MetadataRateLimitedError],
)
async def test_tmdb_outage_during_matching_stops_the_cinema(
    failure_type: type[MetadataFailure],
) -> None:
    """An outage or rate limit stops the import before any movie is created."""
    provider = _fake_tmdb(
        {"Down": (_tmdb_movie("1", "Down"),), "Good": (_tmdb_movie("2", "Good"),)},
        {"1": failure_type("down")},
    )
    movies = _movies()
    with pytest.raises(MovieMetadataUnavailableError):
        await _import_with_tmdb(movies, provider, "Good", "Down")
    movies.create_or_reuse.assert_not_awaited()


@pytest.mark.asyncio
async def test_cinema_import_reports_skipped_and_unmatched_movies() -> None:
    """Skipped and unmatched movies are reported apart, each with its reason."""
    provider = _fake_tmdb(
        {
            "Good": (_tmdb_movie("1", "Good"),),
            "Bad": (_tmdb_movie("2", "Bad"),),
            "Gone": (_tmdb_movie("3", "Gone"),),
        },
        {
            "2": MetadataDetailMappingError("Invalid TMDB response: detail_mapping"),
            "3": MetadataNotFoundError("TMDB record not found"),
        },
    )
    movies = _movies()
    result = await _import_with_tmdb(movies, provider, "Good", "Bad", "Gone", "Lost")
    unresolved = ImportScreeningsCommand.UnresolvedMovieData
    assert result.skipped_movies == (
        unresolved("Bad", "MetadataDetailMappingError"),
        unresolved("Gone", "MetadataNotFoundError"),
    )
    assert result.unmatched_movies == (unresolved("Lost", "no_match"),)
    assert _created_tmdb_ids(movies)["Good"] == "1"


@pytest.mark.asyncio
async def test_truncated_search_reports_the_movie_as_uncertain() -> None:
    """A search that cannot be read in full skips the movie as uncertain."""
    provider = _fake_tmdb({}, {})
    provider.search_movies.side_effect = None
    provider.search_movies.return_value = MetadataBatch((), False)
    result = await _import_with_tmdb(_movies(), provider, "Partial")
    assert result.skipped_movies == (
        ImportScreeningsCommand.UnresolvedMovieData("Partial", "uncertain"),
    )
    assert result.unmatched_movies == ()
