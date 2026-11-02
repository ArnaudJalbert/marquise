"""Command use case for importing screenings from an assigned source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from marquise.application.queries.fetch_screenings_from_source import (
    FetchScreeningsFromSourceQuery,
)
from marquise.application.use_cases.create_missing_movies import (
    CreateMissingMoviesCommand,
)
from marquise.application.use_cases.create_screenings import CreateScreeningsCommand


class ImportScreeningsCommand:
    """Fetch source screenings, create missing movies, and persist screenings."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        cinema_id: str
        start_date: date
        end_date: date

        def __post_init__(self) -> None:
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
        fetch_screenings_use_case: FetchScreeningsFromSourceQuery,
        create_movies_use_case: CreateMissingMoviesCommand,
        create_screenings_use_case: CreateScreeningsCommand,
    ) -> None:
        self.fetch_screenings_use_case = fetch_screenings_use_case
        self.create_movies_use_case = create_movies_use_case
        self.create_screenings_use_case = create_screenings_use_case

    async def execute(self, input_data: InputData) -> OutputData:
        fetched = await self.fetch_screenings_use_case.execute(
            FetchScreeningsFromSourceQuery.InputData(
                cinema_id=input_data.cinema_id,
                start_date=input_data.start_date,
                end_date=input_data.end_date,
            )
        )
        movies = await self.create_movies_use_case.execute(
            CreateMissingMoviesCommand.InputData(
                movies=tuple(
                    CreateMissingMoviesCommand.MovieInput(
                        title=movie.title,
                        identity_title=movie.identity_title,
                        source_identifier=movie.identifier,
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
                    for movie in fetched.movies
                )
            )
        )
        title_to_id = {
            (_normalize_title(movie.title).lower(), movie.source_identifier): movie.id
            for movie in movies.movies
        }
        screenings = await self.create_screenings_use_case.execute(
            CreateScreeningsCommand.InputData(
                screenings=tuple(
                    CreateScreeningsCommand.ScreeningInput(
                        movie_id=title_to_id[
                            (
                                _normalize_title(screening.movie_title).lower(),
                                screening.identifier,
                            )
                        ],
                        movie_title=screening.movie_title,
                        cinema_id=fetched.cinema_id,
                        cinema_name=fetched.cinema_name,
                        showtime=screening.showtime,
                        external_id=screening.external_id,
                        source_name=fetched.source_name,
                        ticket_url=screening.ticket_url,
                        room=screening.room,
                        language=screening.language,
                    )
                    for screening in fetched.screenings
                )
            )
        )
        return self.OutputData(
            cinema_id=fetched.cinema_id,
            cinema_name=fetched.cinema_name,
            source_name=fetched.source_name,
            screenings=tuple(
                self.ScreeningData(
                    movie_title=item.movie_title,
                    showtime=item.showtime,
                    imported=item.imported,
                    rescheduled=item.rescheduled,
                )
                for item in screenings.screenings
            ),
            total_count=screenings.total_count,
            imported_count=screenings.imported_count,
            updated_count=screenings.updated_count,
            rescheduled_count=screenings.rescheduled_count,
            skipped_count=screenings.skipped_count,
        )


def _normalize_title(title: str) -> str:
    """Strip and collapse internal whitespace in a movie title."""
    return " ".join(title.strip().split())
