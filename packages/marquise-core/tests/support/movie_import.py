"""Run the real import pipeline with deterministic mocks at its edges."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, create_autospec

from marquise.application.metadata import ProviderIdentity
from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.queries.find_stored_movies import FindStoredMoviesQuery
from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.create_movies import CreateMoviesCommand
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.enrich_movies import EnrichMoviesUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.match_movies import MatchMoviesUseCase
from marquise.application.use_cases.resolve_movies import ResolveMoviesCommand

DAY = datetime(2026, 10, 31, 19, tzinfo=UTC)


def autospec_use_case(use_case: type) -> AsyncMock:
    """Autospec a use case, keeping its real inner classes for callers."""
    mock = create_autospec(use_case, instance=True)
    for name, value in vars(use_case).items():
        if isinstance(value, type):
            setattr(mock, name, value)
    return mock


@dataclass(frozen=True, slots=True)
class Outcome:
    """What the matcher answers for one movie."""

    status: str
    identity: ProviderIdentity | None = None
    titles: tuple[str, ...] = ()
    release_year: int | None = None


def build_match(tmdb_id: str) -> Outcome:
    """Return a confirmed TMDB match."""
    return Outcome("matched", ProviderIdentity("tmdb", tmdb_id))


def build_matcher(*outcomes: Outcome) -> AsyncMock:
    """Return a matcher answering each movie in order, or never matching."""
    remaining = list(outcomes)

    def answer(
        request: MatchMoviesUseCase.InputData,
    ) -> MatchMoviesUseCase.OutputData:
        return MatchMoviesUseCase.OutputData(
            tuple(
                MatchMoviesUseCase.MovieMatch(
                    movie,
                    outcome.status,
                    outcome.identity,
                    outcome.titles,
                    outcome.release_year,
                )
                for movie in request.movies
                for outcome in [remaining.pop(0) if remaining else Outcome("unmatched")]
            )
        )

    matcher = autospec_use_case(MatchMoviesUseCase)
    matcher.execute.side_effect = answer
    return matcher


def build_unchanged_enricher() -> AsyncMock:
    """Return an enricher that leaves every movie as it is."""
    enricher = autospec_use_case(EnrichMoviesUseCase)
    enricher.execute.return_value = EnrichMoviesUseCase.OutputData(())
    return enricher


def import_command(
    fetch_screenings: FetchScreeningsFromSourceQuery,
    movies: MovieRepository,
    create_screenings: CreateScreeningsCommand,
    matcher: MatchMoviesUseCase | None = None,
    enricher: EnrichMoviesUseCase | None = None,
) -> ImportScreeningsCommand:
    """Build the real coordinator, mocking whatever a test doesn't exercise."""
    return ImportScreeningsCommand(
        fetch_screenings,
        ResolveMoviesCommand(
            matcher or build_matcher(),
            FindStoredMoviesQuery(movies),
            CreateMoviesCommand(movies),
        ),
        create_screenings,
        enricher or build_unchanged_enricher(),
    )


class MovieImport:
    """Import source movies through the real pipeline and report their links."""

    @dataclass(frozen=True, slots=True)
    class MovieData:
        title: str
        id: str
        source_identifier: str | None = None

    @dataclass(frozen=True, slots=True)
    class OutputData:
        movies: tuple["MovieImport.MovieData", ...]

    @dataclass(frozen=True, slots=True)
    class InputData:
        movies: tuple[FetchScreeningsFromSourceQuery.FetchedMovieData, ...]

    @staticmethod
    def build_movie_input(
        title: str, source_identifier: str | None = None, **details: object
    ) -> FetchScreeningsFromSourceQuery.FetchedMovieData:
        """Build one fetched movie."""
        return FetchScreeningsFromSourceQuery.FetchedMovieData(
            title=title, identifier=source_identifier, **details
        )

    def __init__(
        self,
        movies: MovieRepository,
        matcher: MatchMoviesUseCase | None = None,
        enricher: EnrichMoviesUseCase | None = None,
    ) -> None:
        self._movies = movies
        self._matcher = matcher
        self._enricher = enricher

    async def execute(self, input_data: InputData) -> OutputData:
        """Run the import with one screening per movie."""
        create_screenings = autospec_use_case(CreateScreeningsCommand)
        create_screenings.execute.return_value = CreateScreeningsCommand.OutputData(
            (), 0, 0, 0, 0
        )
        command = import_command(
            self._fetch(input_data.movies),
            self._movies,
            create_screenings,
            self._matcher,
            self._enricher,
        )
        await command.execute(
            command.InputData("cinema", date(2026, 10, 31), DAY.date())
        )
        screenings = create_screenings.execute.await_args.args[0].screenings
        return self.OutputData(
            tuple(
                self.MovieData(
                    " ".join(movie.title.split()), screening.movie_id, movie.identifier
                )
                for movie, screening in zip(input_data.movies, screenings, strict=True)
            )
        )

    @staticmethod
    def _fetch(
        movies: tuple[FetchScreeningsFromSourceQuery.FetchedMovieData, ...],
    ) -> AsyncMock:
        fetch = autospec_use_case(FetchScreeningsFromSourceQuery)
        fetch.execute.return_value = FetchScreeningsFromSourceQuery.OutputData(
            cinema_id="cinema",
            cinema_name="Cinema",
            source_name="source",
            movies=movies,
            screenings=tuple(
                FetchScreeningsFromSourceQuery.FetchedScreeningData(
                    movie_title=movie.title, showtime=DAY, identifier=movie.identifier
                )
                for movie in movies
            ),
        )
        return fetch


def build_movie_import(
    movies: MovieRepository,
    matcher: MatchMoviesUseCase | None = None,
    enricher: EnrichMoviesUseCase | None = None,
) -> MovieImport:
    """Build the pipeline harness."""
    return MovieImport(movies, matcher, enricher)
