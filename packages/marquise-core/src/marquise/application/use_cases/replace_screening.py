"""Fully replace screening use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marquise.application.exceptions import CinemaNotFoundError, MovieNotFoundError
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    ScreeningRepository,
)
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime


class ReplaceScreeningUseCase:
    """Use case for fully replacing a screening identified by ID.

    All fields are written. ``None`` optional fields clear the stored
    value. Movie, cinema, and showtime may change; the screening ID
    stays the same.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for replacing a screening.

        Attributes:
            screening_id: Unique identifier of the screening to replace.
            movie_id: Replacement movie ID.
            cinema_id: Replacement cinema ID.
            showtime: Replacement timezone-aware screening time.
            ticket_url: Replacement ticket URL, or None to clear.
            room: Replacement room name, or None to clear.
            language: Replacement language, or None to clear.
            external_id: Replacement source identifier, or None to clear.
        """

        screening_id: str
        movie_id: str
        cinema_id: str
        showtime: datetime
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None
        external_id: str | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If required IDs are empty, showtime is naive, or
                    optional strings are provided but whitespace-only.
            """
            if not self.screening_id.strip():
                raise ValueError("screening_id must not be empty")
            if not self.movie_id.strip():
                raise ValueError("movie_id must not be empty")
            if not self.cinema_id.strip():
                raise ValueError("cinema_id must not be empty")
            if self.showtime.tzinfo is None:
                raise ValueError("showtime must be timezone-aware")
            if self.ticket_url is not None and not self.ticket_url.strip():
                raise ValueError("ticket_url must not be empty when provided")
            if self.room is not None and not self.room.strip():
                raise ValueError("room must not be empty when provided")
            if self.language is not None and not self.language.strip():
                raise ValueError("language must not be empty when provided")
            if self.external_id is not None and not self.external_id.strip():
                raise ValueError("external_id must not be empty when provided")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after a successful full replace.

        Attributes:
            id: The unique identifier of the replaced screening.
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
        """Fully replace an existing screening.

        Args:
            request: The input data for the replacement.

        Returns:
            The output data containing the replaced screening details.

        Raises:
            ScreeningNotFoundError: If no screening with the given ID exists.
            MovieNotFoundError: If no movie with the given ID exists.
            CinemaNotFoundError: If no cinema with the given ID exists.
            ScreeningAlreadyExistsError: If the replacement identity
                collides with another screening.
        """
        existing = await self.screening_repository.find_by_id(
            ScreeningId(value=request.screening_id)
        )
        movie = await self._resolve_movie(request.movie_id, existing.movie)
        cinema = await self._resolve_cinema(request.cinema_id, existing.cinema)

        replaced = await self.screening_repository.replace(
            Screening(
                id=existing.id,
                movie=movie,
                cinema=cinema,
                showtime=Showtime(value=request.showtime),
                external_id=request.external_id,
                ticket_url=request.ticket_url,
                room=request.room,
                language=request.language,
            )
        )

        return self.OutputData(
            id=str(replaced.id),
            movie_id=str(replaced.movie.id),
            movie_title=replaced.movie.title,
            cinema_id=str(replaced.cinema.id),
            cinema_name=replaced.cinema.name,
            showtime=replaced.showtime.value,
            ticket_url=replaced.ticket_url,
            room=replaced.room,
            language=replaced.language,
        )

    async def _resolve_movie(self, movie_id: str, existing: Movie) -> Movie:
        if movie_id == str(existing.id):
            return existing
        movie = await self.movie_repository.find_by_id(MovieId(value=movie_id))
        if movie is None:
            raise MovieNotFoundError(f"A movie with ID '{movie_id}' was not found")
        return movie

    async def _resolve_cinema(self, cinema_id: str, existing: Cinema) -> Cinema:
        if cinema_id == str(existing.id):
            return existing
        cinema = await self.cinema_repository.find_by_id(CinemaId(value=cinema_id))
        if cinema is None:
            raise CinemaNotFoundError(f"A cinema with ID '{cinema_id}' was not found")
        return cinema
