"""Command use case for importing screenings from an assigned source."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from marquise.application.queries.fetch_screenings_from_source import (
        FetchScreeningsFromSourceQuery,
    )
    from marquise.application.use_cases.create_screenings import (
        CreateScreeningsCommand,
    )
    from marquise.application.use_cases.enrich_movies import EnrichMoviesUseCase
    from marquise.application.use_cases.resolve_movies import ResolveMoviesCommand

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
    class OutputData:
        cinema_id: str
        cinema_name: str
        source_name: str
        screenings: tuple[ImportScreeningsCommand.ScreeningData, ...]
        total_count: int
        imported_count: int
        updated_count: int
        skipped_count: int
        rescheduled_count: int = 0

    def __init__(
        self,
        fetch_screenings: FetchScreeningsFromSourceQuery,
        resolve_movies: ResolveMoviesCommand,
        create_screenings: CreateScreeningsCommand,
        enrich_movies: EnrichMoviesUseCase,
    ) -> None:
        self._fetch_screenings = fetch_screenings
        self._resolve_movies = resolve_movies
        self._create_screenings = create_screenings
        self._enrich_movies = enrich_movies

    async def execute(self, input_data: InputData) -> OutputData:
        """Import a cinema's screenings and the movies behind them.

        Screenings are saved before enrichment, so a provider outage during
        enrichment fails the import without losing them. Running it again is
        safe, because stored movies and screenings are reused.

        Args:
            input_data: The cinema and the dates to import.

        Returns:
            What was imported, with one summary per screening.
        """
        source_data = await self._fetch(input_data)
        resolved = await self._resolve_source_movies(source_data)
        saved = await self._save_screenings(source_data, resolved)
        await self._enrich_resolved_movies(resolved)
        logger.info("Imported %d screenings", saved.imported_count)
        return self._build_output(source_data, saved)

    async def _fetch(
        self, input_data: InputData
    ) -> FetchScreeningsFromSourceQuery.OutputData:
        """Fetch the cinema's source movies and screenings."""
        request = self._fetch_screenings.InputData(
            cinema_id=input_data.cinema_id,
            start_date=input_data.start_date,
            end_date=input_data.end_date,
        )
        return await self._fetch_screenings.execute(request)

    async def _resolve_source_movies(
        self, source_data: FetchScreeningsFromSourceQuery.OutputData
    ) -> ResolveMoviesCommand.OutputData:
        """Tie each fetched movie to a stored movie."""
        request = self._build_resolve_request(source_data)
        return await self._resolve_movies.execute(request)

    def _build_resolve_request(
        self, source_data: FetchScreeningsFromSourceQuery.OutputData
    ) -> ResolveMoviesCommand.InputData:
        """Reformat fetched movies for resolving."""
        return self._resolve_movies.InputData(
            movies=tuple(
                self._resolve_movies.MovieInput(
                    title=movie.title,
                    source_identifier=movie.identifier,
                    identity_title=movie.identity_title,
                    description=movie.description,
                    directors=movie.directors,
                    cast=movie.cast,
                    duration_minutes=movie.duration_minutes,
                    release_year=movie.release_year,
                    poster_url=movie.poster_url,
                    trailer_url=movie.trailer_url,
                    genres=movie.genres,
                    original_title=movie.original_title,
                    rating=movie.rating,
                    origin_countries=movie.origin_countries,
                )
                for movie in source_data.movies
            )
        )

    async def _save_screenings(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        resolved: ResolveMoviesCommand.OutputData,
    ) -> CreateScreeningsCommand.OutputData:
        """Save the fetched screenings, linked to their movies."""
        request = self._build_screenings_request(source_data, resolved)
        return await self._create_screenings.execute(request)

    def _build_screenings_request(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        resolved: ResolveMoviesCommand.OutputData,
    ) -> CreateScreeningsCommand.InputData:
        """Reformat fetched screenings, linking each one to its movie."""
        movie_ids = self._map_movie_ids(resolved)
        return self._create_screenings.InputData(
            screenings=tuple(
                self._build_screening_input(
                    source_data,
                    screening,
                    movie_ids[self._build_screening_key(screening)],
                )
                for screening in source_data.screenings
            )
        )

    def _map_movie_ids(
        self, resolved: ResolveMoviesCommand.OutputData
    ) -> dict[tuple[str, str | None], str]:
        """Index movie IDs by the title and source identifier screenings carry."""
        return {
            (self._normalize_title_key(movie.title), movie.source_identifier): (
                movie.movie_id
            )
            for movie in resolved.movies
        }

    def _build_screening_key(
        self, screening: FetchScreeningsFromSourceQuery.FetchedScreeningData
    ) -> tuple[str, str | None]:
        """Build the key a screening's movie is indexed under."""
        return self._normalize_title_key(screening.movie_title), screening.identifier

    @staticmethod
    def _normalize_title_key(title: str) -> str:
        """Ignore the case and spacing differences sources put in titles."""
        return " ".join(title.strip().split()).lower()

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

    async def _enrich_resolved_movies(
        self, resolved: ResolveMoviesCommand.OutputData
    ) -> None:
        """Enrich every resolved movie."""
        request = self._enrich_movies.InputData(
            movies=tuple(
                self._enrich_movies.MovieInput(movie.movie_id, movie.tmdb_id)
                for movie in resolved.movies
            )
        )
        await self._enrich_movies.execute(request)

    def _build_output(
        self,
        source_data: FetchScreeningsFromSourceQuery.OutputData,
        saved: CreateScreeningsCommand.OutputData,
    ) -> OutputData:
        """Reformat the saved screenings as this use case's output."""
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
        )
