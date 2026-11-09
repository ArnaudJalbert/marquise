"""Run the real import pipeline with deterministic mocks at its edges."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, NonCallableMagicMock, create_autospec

from marquise.application.metadata import ProviderIdentity
from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.queries.find_stored_movies import FindStoredMoviesQuery
from marquise.application.queries.link_screenings import LinkScreeningsQuery
from marquise.application.repositories import MovieRepository
from marquise.application.use_cases.create_movies import CreateMoviesCommand
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand
from marquise.application.use_cases.enrich_movies import EnrichMoviesUseCase
from marquise.application.use_cases.import_screenings import ImportScreeningsCommand
from marquise.application.use_cases.match_movies import MatchMoviesUseCase
from marquise.domain.entities import Movie

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
    enricher.execute.return_value = EnrichMoviesUseCase.OutputData((), ())
    return enricher


def import_command(
    fetch_screenings: FetchScreeningsFromSourceQuery,
    movies: MovieRepository,
    create_screenings: CreateScreeningsCommand,
    matcher: MatchMoviesUseCase | None = None,
    enricher: EnrichMoviesUseCase | None = None,
) -> ImportScreeningsCommand:
    """Build the real coordinator, mocking whatever a test doesn't exercise."""
    if isinstance(movies, NonCallableMagicMock):
        remember_created_movies(movies)
    return ImportScreeningsCommand(
        fetch_screenings,
        matcher or build_matcher(),
        FindStoredMoviesQuery(movies),
        CreateMoviesCommand(movies),
        LinkScreeningsQuery(),
        create_screenings,
        enricher or build_unchanged_enricher(),
    )


def remember_created_movies(movies: NonCallableMagicMock) -> None:
    """Make a repository mock return the movies it created, like a database.

    The import looks movies up again after creating them, so a mock that
    forgot them would hide every created movie from that second lookup.
    """
    if getattr(movies, "remembers_created_movies", False):
        return
    movies.remembers_created_movies = True
    created: list[Movie] = []
    create = _configured_behaviour(movies.create_or_reuse)
    find_by_tmdb_id = _configured_behaviour(movies.find_by_tmdb_id)
    find_by_titles = _configured_behaviour(movies.find_by_titles)

    def save(movie: Movie) -> Movie:
        saved = create(movie)
        created.append(saved)
        return saved

    def find_created_by_tmdb_id(tmdb_id: str) -> Movie | None:
        found = [movie for movie in created if movie.tmdb_id == tmdb_id]
        return found[0] if found else find_by_tmdb_id(tmdb_id)

    movies.create_or_reuse.side_effect = save
    movies.find_by_tmdb_id.side_effect = find_created_by_tmdb_id
    movies.find_by_titles.side_effect = lambda terms: [
        *find_by_titles(terms),
        *created,
    ]


def _configured_behaviour(method: AsyncMock) -> Callable[[object], object]:
    """Return what a mocked method was set up to do, as a plain function."""
    effect = method.side_effect
    if effect is None:
        return lambda _: method.return_value
    if isinstance(effect, BaseException) or (
        isinstance(effect, type) and issubclass(effect, BaseException)
    ):
        raise_effect = effect

        def raise_configured(_: object) -> object:
            raise raise_effect

        return raise_configured
    if callable(effect):
        return effect
    return lambda _: next(effect)


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
        skipped_movies: tuple[ImportScreeningsCommand.UnresolvedMovieData, ...] = ()
        unmatched_movies: tuple[ImportScreeningsCommand.UnresolvedMovieData, ...] = ()

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
        imported = await command.execute(
            command.InputData("cinema", date(2026, 10, 31), DAY.date())
        )
        screenings = create_screenings.execute.await_args.args[0].screenings
        return self.OutputData(
            tuple(
                self.MovieData(
                    " ".join(movie.title.split()), screening.movie_id, movie.identifier
                )
                for movie, screening in zip(input_data.movies, screenings, strict=True)
            ),
            imported.skipped_movies,
            imported.unmatched_movies,
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
