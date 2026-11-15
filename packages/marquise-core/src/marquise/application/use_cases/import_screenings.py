"""Command use case for importing screenings from an assigned source."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from marquise.application.metadata import MatchReason
    from marquise.application.queries.fetch_screenings_from_source import (
        FetchScreeningsFromSourceQuery,
    )
    from marquise.application.queries.find_stored_movies import FindStoredMoviesQuery
    from marquise.application.queries.link_screenings import LinkScreeningsQuery
    from marquise.application.use_cases.create_movies import CreateMoviesCommand
    from marquise.application.use_cases.create_screenings import (
        CreateScreeningsCommand,
    )
    from marquise.application.use_cases.enrich_movies import EnrichMoviesUseCase
    from marquise.application.use_cases.match_movies import MatchMoviesUseCase

logger = logging.getLogger(__name__)


class ImportScreeningsCommand:
    """Coordinate one cinema's import, from fetching to enrichment.

    Only sequences use cases and reformats data between them.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        cinema_id: str
        start_date: date
        end_date: date

        def __post_init__(self) -> None:
            if not isinstance(self.cinema_id, str):
                raise TypeError("cinema_id must be a string")
            if not isinstance(self.start_date, date):
                raise TypeError("start_date must be a date")
            if not isinstance(self.end_date, date):
                raise TypeError("end_date must be a date")
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if self.start_date > self.end_date:
                raise ValueError("start_date must not be after end_date")

    @dataclass(frozen=True, slots=True)
    class ScreeningData:
        """Summary of a single imported or already-existing screening.

        Attributes:
            movie_title: The title of the movie.
            showtime: The showtime in ISO format.
            imported: True if newly created.
            rescheduled: True if an existing screening moved to a new showtime.
        """

        movie_title: str
        showtime: str
        imported: bool
        rescheduled: bool = False

    @dataclass(frozen=True, slots=True)
    class UnresolvedMovieData:
        """A fetched movie imported without a TMDB identity, and why.

        Attributes:
            title: The raw title the cinema listed.
            reason: A stable name from a fixed list, comparable across runs.
        """

        title: str
        reason: MatchReason

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """What one cinema import did.

        Attributes:
            skipped_movies: Movies left without an identity because TMDB data
                was bad or matching was uncertain.
            unmatched_movies: Movies with no matching TMDB record.
        """

        cinema_id: str
        cinema_name: str
        source_name: str
        screenings: tuple[ImportScreeningsCommand.ScreeningData, ...]
        total_count: int
        imported_count: int
        updated_count: int
        skipped_count: int
        rescheduled_count: int = 0
        skipped_movies: tuple[ImportScreeningsCommand.UnresolvedMovieData, ...] = ()
        unmatched_movies: tuple[ImportScreeningsCommand.UnresolvedMovieData, ...] = ()

    def __init__(
        self,
        fetch_screenings: FetchScreeningsFromSourceQuery,
        match_movies: MatchMoviesUseCase,
        find_stored_movies: FindStoredMoviesQuery,
        create_movies: CreateMoviesCommand,
        link_screenings: LinkScreeningsQuery,
        create_screenings: CreateScreeningsCommand,
        enrich_movies: EnrichMoviesUseCase,
    ) -> None:
        self._fetch_screenings = fetch_screenings
        self._match_movies = match_movies
        self._find_stored_movies = find_stored_movies
        self._create_movies = create_movies
        self._link_screenings = link_screenings
        self._create_screenings = create_screenings
        self._enrich_movies = enrich_movies

    async def execute(self, input_data: InputData) -> OutputData:
        """Import a cinema's screenings and the movies behind them.

        Missing movies are created, then looked up again, so every screening
        links through a query. Expected missing or invalid metadata leaves a
        movie not enriched. Metadata outages and unexpected errors propagate
        after screenings are saved.
        Running it again is safe, because stored movies and screenings are reused.
        The Raises section covers enrichment only. Source fetch and matching
        errors also propagate.

        Args:
            input_data: The cinema and the dates to import.

        Returns:
            What was imported, with one summary per screening.

        Raises:
            MetadataFailure: If enrichment fails for a reason other than missing
                or invalid metadata.
            MovieWorkflowConflictError: If enrichment cannot resolve an identity
                or write conflict.
            ValueError: If the enrichment clock returns a timestamp without a
                timezone.
        """
        source_data = await self._fetch(
            input_data.cinema_id, input_data.start_date, input_data.end_date
        )
        matches = await self._match_source_movies(source_data)
        first_lookup = await self._look_up_stored_movies(matches)
        await self._create_missing_movies(source_data, first_lookup)
        stored_movies = await self._look_up_stored_movies(matches)
        links = await self._link_source_screenings(source_data, stored_movies)
        saved = await self._save_screenings(source_data, links)
        await self._enrich_stored_movies(stored_movies)
        logger.info("Imported %d screenings", saved.imported_count)
        return self._build_output(source_data, saved, matches)

    async def _fetch(
        self, cinema_id: str, start_date: date, end_date: date
    ) -> FetchScreeningsFromSourceQuery.OutputData:
        """Fetch the cinema's source movies and screenings."""
        request = self._fetch_screenings.InputData(
            cinema_id=cinema_id, start_date=start_date, end_date=end_date
        )
        return await self._fetch_screenings.execute(request)

    async def _match_source_movies(
        self, source_data: FetchScreeningsFromSourceQuery.OutputData
    ) -> MatchMoviesUseCase.OutputData:
        """Find each fetched movie's identity."""
        request = self._build_match_request(source_data)
        return await self._match_movies.execute(request)

    def _build_match_request(
        self, source_data: FetchScreeningsFromSourceQuery.OutputData
    ) -> MatchMoviesUseCase.InputData:
        """Reformat fetched movies for matching."""
        return self._match_movies.InputData(
            movies=tuple(
                self._match_movies.MovieInput(
                    title=movie.title,
                    release_year=movie.release_year,
                    directors=movie.directors or (),
                    duration_minutes=movie.duration_minutes,
                    identity_title=movie.identity_title,
                    source_identifier=movie.identifier,
                )
                for movie in source_data.movies
            )
        )

    async def _look_up_stored_movies(
        self, matches: MatchMoviesUseCase.OutputData
    ) -> FindStoredMoviesQuery.OutputData:
        """Sort matched movies into stored and missing."""
        request = self._build_find_request(matches)
        return await self._find_stored_movies.execute(request)

    def _build_find_request(
        self, matches: MatchMoviesUseCase.OutputData
    ) -> FindStoredMoviesQuery.InputData:
        """Reformat matches for the stored movie lookup."""
        return self._find_stored_movies.InputData(
            movies=tuple(
                self._find_stored_movies.MovieInput(
                    title=match.source.title,
                    source_identifier=match.source.source_identifier,
                    release_year=match.source.release_year,
                    matched_release_year=match.release_year,
                    identity=match.identity,
                    matched_titles=match.titles,
                )
                for match in matches.matches
            )
        )

    async def _create_missing_movies(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        lookup: FindStoredMoviesQuery.OutputData,
    ) -> None:
        """Create the movies the lookup found missing."""
        request = self._build_create_request(source_data, lookup)
        await self._create_movies.execute(request)

    def _build_create_request(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        lookup: FindStoredMoviesQuery.OutputData,
    ) -> CreateMoviesCommand.InputData:
        """Reformat missing movies, adding the details fetched for each one."""
        details = {
            (movie.title, movie.identifier): movie for movie in source_data.movies
        }
        return self._create_movies.InputData(
            movies=tuple(
                self._build_create_input(
                    movie, details[(movie.title, movie.source_identifier)]
                )
                for movie in lookup.missing
            )
        )

    def _build_create_input(
        self,
        missing: FindStoredMoviesQuery.MissingMovie,
        details: FetchScreeningsFromSourceQuery.FetchedMovieData,
    ) -> CreateMoviesCommand.MovieInput:
        """Reformat one missing movie and its fetched details."""
        return self._create_movies.MovieInput(
            saved_title=missing.saved_title,
            key=missing.key,
            tmdb_id=missing.tmdb_id,
            release_year=missing.release_year,
            description=details.description,
            directors=details.directors,
            cast=details.cast,
            duration_minutes=details.duration_minutes,
            poster_url=details.poster_url,
            trailer_url=details.trailer_url,
            genres=details.genres,
            original_title=details.original_title,
            rating=details.rating,
            origin_countries=details.origin_countries,
        )

    async def _link_source_screenings(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        stored_movies: FindStoredMoviesQuery.OutputData,
    ) -> LinkScreeningsQuery.OutputData:
        """Find the movie each fetched screening belongs to."""
        request = self._build_link_request(source_data, stored_movies)
        return await self._link_screenings.execute(request)

    def _build_link_request(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        stored_movies: FindStoredMoviesQuery.OutputData,
    ) -> LinkScreeningsQuery.InputData:
        """Reformat fetched screenings and stored movies for linking."""
        return self._link_screenings.InputData(
            screenings=tuple(
                self._link_screenings.ScreeningInput(
                    screening.movie_title, screening.identifier
                )
                for screening in source_data.screenings
            ),
            movies=tuple(
                self._link_screenings.MovieInput(
                    movie.title, movie.movie_id, movie.source_identifier
                )
                for movie in stored_movies.stored
            ),
        )

    async def _save_screenings(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        links: LinkScreeningsQuery.OutputData,
    ) -> CreateScreeningsCommand.OutputData:
        """Save the fetched screenings, each with its movie."""
        request = self._build_screenings_request(source_data, links)
        return await self._create_screenings.execute(request)

    def _build_screenings_request(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        links: LinkScreeningsQuery.OutputData,
    ) -> CreateScreeningsCommand.InputData:
        """Reformat fetched screenings with the movie each one links to."""
        return self._create_screenings.InputData(
            screenings=tuple(
                self._build_screening_input(source_data, screening, movie_id)
                for screening, movie_id in zip(
                    source_data.screenings, links.movie_ids, strict=True
                )
            )
        )

    def _build_screening_input(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        screening: FetchScreeningsFromSourceQuery.FetchedScreeningData,
        movie_id: str,
    ) -> CreateScreeningsCommand.ScreeningInput:
        """Reformat one fetched screening."""
        return self._create_screenings.ScreeningInput(
            movie_id=movie_id,
            movie_title=screening.movie_title,
            cinema_id=source_data.cinema_id,
            cinema_name=source_data.cinema_name,
            showtime=screening.showtime,
            external_id=screening.external_id,
            source_name=source_data.source_name,
            ticket_url=screening.ticket_url,
            room=screening.room,
            language=screening.language,
        )

    async def _enrich_stored_movies(
        self, stored_movies: FindStoredMoviesQuery.OutputData
    ) -> None:
        """Enrich every stored movie, with its identity when matching found one."""
        request = self._enrich_movies.InputData(
            movies=tuple(
                self._enrich_movies.MovieInput(movie.movie_id, movie.tmdb_id)
                for movie in stored_movies.stored
            )
        )
        await self._enrich_movies.execute(request)

    def _build_output(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        saved: CreateScreeningsCommand.OutputData,
        matches: MatchMoviesUseCase.OutputData,
    ) -> OutputData:
        """Reformat the saved screenings and unresolved movies as output."""
        return self.OutputData(
            cinema_id=source_data.cinema_id,
            cinema_name=source_data.cinema_name,
            source_name=source_data.source_name,
            screenings=tuple(
                self.ScreeningData(
                    movie_title=item.movie_title,
                    showtime=item.showtime,
                    imported=item.imported,
                    rescheduled=item.rescheduled,
                )
                for item in saved.screenings
            ),
            total_count=saved.total_count,
            imported_count=saved.imported_count,
            updated_count=saved.updated_count,
            rescheduled_count=saved.rescheduled_count,
            skipped_count=saved.skipped_count,
            skipped_movies=self._unresolved(matches, "incomplete"),
            unmatched_movies=self._unresolved(matches, "unmatched"),
        )

    def _unresolved(
        self,
        matches: MatchMoviesUseCase.OutputData,
        status: Literal["incomplete", "unmatched"],
    ) -> tuple[UnresolvedMovieData, ...]:
        """Reformat the matches with the given status for the report."""
        unresolved = []
        for match in matches.matches:
            reason = match.reason
            if match.status != status or reason is None:
                continue
            unresolved.append(self.UnresolvedMovieData(match.source.title, reason))
        return tuple(unresolved)
