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
    as_provided_datetime,
    as_provided_optional_str,
    is_provided,
    reject_blank_when_provided,
    require_non_empty,
    require_timezone_aware_showtime,
    screening_output_data,
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
        movie_id: str | object = UNSET
        cinema_id: str | object = UNSET
        showtime: datetime | object = UNSET
        ticket_url: str | None | object = UNSET
        room: str | None | object = UNSET
        language: str | None | object = UNSET
        external_id: str | None | object = UNSET

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If screening_id is empty, a provided identity
                    field is invalid, or optional strings are whitespace-only.
            """
            require_non_empty(self.screening_id, "screening_id")
            if is_provided(self.movie_id):
                require_non_empty(str(self.movie_id), "movie_id")
            if is_provided(self.cinema_id):
                require_non_empty(str(self.cinema_id), "cinema_id")
            if is_provided(self.showtime):
                require_timezone_aware_showtime(as_provided_datetime(self.showtime))
            if is_provided(self.ticket_url):
                reject_blank_when_provided(
                    as_provided_optional_str(self.ticket_url), "ticket_url"
                )
            if is_provided(self.room):
                reject_blank_when_provided(as_provided_optional_str(self.room), "room")
            if is_provided(self.language):
                reject_blank_when_provided(
                    as_provided_optional_str(self.language), "language"
                )
            if is_provided(self.external_id):
                reject_blank_when_provided(
                    as_provided_optional_str(self.external_id), "external_id"
                )

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after a successful update.

        Attributes:
            id: The unique identifier of the updated screening.
            movie_id: The screened movie's ID.
            movie_title: The screened movie's title.
            cinema_id: The hosting cinema's ID.
            cinema_name: The hosting cinema's display name.
            showtime: The screening time.
            ticket_url: Link to purchase tickets (optional).
            room: Room or auditorium name (optional).
            language: Language or subtitle version (optional).
        """

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

    async def execute(self, request: InputData) -> OutputData:
        """Update an existing screening.

        Args:
            request: The input data for the update.

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
            ScreeningId(value=request.screening_id)
        )
        movie = await self._resolve_movie(request.movie_id, existing.movie)
        cinema = await self._resolve_cinema(request.cinema_id, existing.cinema)
        showtime = (
            existing.showtime
            if not is_provided(request.showtime)
            else Showtime(value=as_provided_datetime(request.showtime))
        )
        external_id = (
            existing.external_id
            if not is_provided(request.external_id)
            else as_provided_optional_str(request.external_id)
        )
        ticket_url = (
            existing.ticket_url
            if not is_provided(request.ticket_url)
            else as_provided_optional_str(request.ticket_url)
        )
        room = (
            existing.room
            if not is_provided(request.room)
            else as_provided_optional_str(request.room)
        )
        language = (
            existing.language
            if not is_provided(request.language)
            else as_provided_optional_str(request.language)
        )

        updated = await self.screening_repository.replace(
            Screening(
                id=existing.id,
                movie=movie,
                cinema=cinema,
                showtime=showtime,
                external_id=external_id,
                ticket_url=ticket_url,
                room=room,
                language=language,
            )
        )

        return screening_output_data(self.OutputData, updated)

    async def _resolve_movie(self, movie_id: str | object, existing: Movie) -> Movie:
        if not is_provided(movie_id):
            return existing
        if movie_id == str(existing.id):
            return existing
        movie = await self.movie_repository.find_by_id(MovieId(value=str(movie_id)))
        if movie is None:
            raise MovieNotFoundError(f"A movie with ID '{movie_id}' was not found")
        return movie

    async def _resolve_cinema(
        self, cinema_id: str | object, existing: Cinema
    ) -> Cinema:
        if not is_provided(cinema_id):
            return existing
        if cinema_id == str(existing.id):
            return existing
        cinema = await self.cinema_repository.find_by_id(CinemaId(value=str(cinema_id)))
        if cinema is None:
            raise CinemaNotFoundError(f"A cinema with ID '{cinema_id}' was not found")
        return cinema
