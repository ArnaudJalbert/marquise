"""Update screening use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marquise.application.exceptions import CinemaNotFoundError, MovieNotFoundError
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    ScreeningRepository,
)
from marquise.application.use_cases._screening_helpers import (
    UNSET,
    _Unset,
    is_provided,
    keep,
    reject_blank_when_provided,
    require_non_empty,
    require_timezone_aware_showtime,
)
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime


class UpdateScreeningUseCase:
    """Use case for updating an existing screening.

    Every field except ``screening_id`` is optional. Omitted fields keep their
    stored values; explicit ``None`` clears optional metadata fields.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for updating a screening.

        Attributes:
            screening_id: Unique identifier of the screening to update.
            movie_id: Replacement movie ID, or omitted to leave unchanged.
            cinema_id: Replacement cinema ID, or omitted to leave unchanged.
            showtime: Replacement timezone-aware screening time, or omitted
                to leave unchanged.
            ticket_url: Replacement ticket URL, ``None`` to clear, or omitted
                to leave unchanged.
            room: Replacement room name, ``None`` to clear, or omitted to
                leave unchanged.
            language: Replacement language, ``None`` to clear, or omitted to
                leave unchanged.
            external_id: Replacement source identifier, ``None`` to clear, or
                omitted to leave unchanged.
        """

        screening_id: str
        movie_id: str | _Unset = UNSET
        cinema_id: str | _Unset = UNSET
        showtime: datetime | _Unset = UNSET
        ticket_url: str | None | _Unset = UNSET
        room: str | None | _Unset = UNSET
        language: str | None | _Unset = UNSET
        external_id: str | None | _Unset = UNSET

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If screening_id is empty, a provided identity
                    field is invalid, or optional strings are whitespace-only.
            """
            require_non_empty(self.screening_id, "screening_id")
            if is_provided(self.movie_id):
                require_non_empty(self.movie_id, "movie_id")
            if is_provided(self.cinema_id):
                require_non_empty(self.cinema_id, "cinema_id")
            if is_provided(self.showtime):
                require_timezone_aware_showtime(self.showtime)
            if is_provided(self.ticket_url):
                reject_blank_when_provided(self.ticket_url, "ticket_url")
            if is_provided(self.room):
                reject_blank_when_provided(self.room, "room")
            if is_provided(self.language):
                reject_blank_when_provided(self.language, "language")
            if is_provided(self.external_id):
                reject_blank_when_provided(self.external_id, "external_id")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Persisted screening details and parent display names after an update."""

        id: str
        movie_id: str
        movie_title: str
        cinema_id: str
        cinema_name: str
        showtime: datetime
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None

    def __init__(
        self,
        screening_repository: ScreeningRepository,
        movie_repository: MovieRepository,
        cinema_repository: CinemaRepository,
    ) -> None:
        """Initialize the use case.

        Args:
            screening_repository: A repository for screening persistence.
            movie_repository: A repository for looking up movies.
            cinema_repository: A repository for looking up cinemas.
        """
        self.screening_repository = screening_repository
        self.movie_repository = movie_repository
        self.cinema_repository = cinema_repository

    async def execute(self, input_data: InputData) -> OutputData:
        """Update an existing screening.

        Args:
            input_data: The input data for the update.

        Returns:
            The output data containing the updated screening details.

        Raises:
            ScreeningNotFoundError: If no screening with the given ID exists.
            MovieNotFoundError: If a replacement movie ID does not exist.
            CinemaNotFoundError: If a replacement cinema ID does not exist.
            ScreeningAlreadyExistsError: If the updated identity collides with
                another screening.
        """
        existing = await self.screening_repository.find_by_id(
            ScreeningId(value=input_data.screening_id)
        )
        movie = await self._resolve_movie(input_data.movie_id, existing.movie)
        cinema = await self._resolve_cinema(input_data.cinema_id, existing.cinema)
        showtime = (
            existing.showtime
            if not is_provided(input_data.showtime)
            else Showtime(value=input_data.showtime)
        )

        updated = await self.screening_repository.replace(
            Screening(
                id=existing.id,
                movie=movie,
                cinema=cinema,
                showtime=showtime,
                external_id=keep(existing.external_id, input_data.external_id),
                ticket_url=keep(existing.ticket_url, input_data.ticket_url),
                room=keep(existing.room, input_data.room),
                language=keep(existing.language, input_data.language),
            ),
            fields=frozenset(
                name
                for name, value in (
                    ("movie_id", input_data.movie_id),
                    ("cinema_id", input_data.cinema_id),
                    ("showtime", input_data.showtime),
                    ("external_id", input_data.external_id),
                    ("ticket_url", input_data.ticket_url),
                    ("room", input_data.room),
                    ("language", input_data.language),
                )
                if is_provided(value)
            ),
        )

        return self.OutputData(
            id=str(updated.id),
            movie_id=str(updated.movie.id),
            movie_title=updated.movie.title,
            cinema_id=str(updated.cinema.id),
            cinema_name=updated.cinema.name,
            showtime=updated.showtime.value,
            ticket_url=updated.ticket_url,
            room=updated.room,
            language=updated.language,
        )

    async def _resolve_movie(self, movie_id: str | _Unset, existing: Movie) -> Movie:
        if not is_provided(movie_id):
            return existing
        if movie_id == str(existing.id):
            return existing
        movie = await self.movie_repository.find_by_id(MovieId(value=str(movie_id)))
        if movie is None:
            raise MovieNotFoundError(f"A movie with ID '{movie_id}' was not found")
        return movie

    async def _resolve_cinema(
        self, cinema_id: str | _Unset, existing: Cinema
    ) -> Cinema:
        if not is_provided(cinema_id):
            return existing
        if cinema_id == str(existing.id):
            return existing
        cinema = await self.cinema_repository.find_by_id(CinemaId(value=str(cinema_id)))
        if cinema is None:
            raise CinemaNotFoundError(f"A cinema with ID '{cinema_id}' was not found")
        return cinema
