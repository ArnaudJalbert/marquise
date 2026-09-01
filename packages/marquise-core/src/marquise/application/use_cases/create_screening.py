"""Create screening use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from marquise.application.exceptions import CinemaNotFoundError, MovieNotFoundError
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    ScreeningRepository,
)
from marquise.domain.entities import Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime


class CreateScreeningUseCase:
    """Use case for creating a single screening record.

    Looks up the movie and cinema, generates a unique ID, persists the
    screening, and returns use-case output data.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for creating a screening.

        Attributes:
            movie_id: Unique identifier of the movie being screened.
            cinema_id: Unique identifier of the hosting cinema.
            showtime: Timezone-aware screening time.
            ticket_url: Link to purchase tickets (optional).
            room: Room or auditorium name (optional).
            language: Language or subtitle version (optional).
            external_id: Source-native identifier (optional).
        """

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
        """Output data returned after successful screening creation.

        Attributes:
            id: The generated unique ID of the screening.
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
            screening_repository: A repository for persisting screenings.
            movie_repository: A repository for looking up movies.
            cinema_repository: A repository for looking up cinemas.
        """
        self.screening_repository = screening_repository
        self.movie_repository = movie_repository
        self.cinema_repository = cinema_repository

    async def execute(self, request: InputData) -> OutputData:
        """Create a new screening.

        Args:
            request: The input data for screening creation.

        Returns:
            The output data containing the created screening details.

        Raises:
            MovieNotFoundError: If no movie with the given ID exists.
            CinemaNotFoundError: If no cinema with the given ID exists.
            ScreeningAlreadyExistsError: If a screening with the same
                cinema, movie, and showtime already exists.
        """
        movie = await self.movie_repository.find_by_id(MovieId(value=request.movie_id))
        if movie is None:
            raise MovieNotFoundError(
                f"A movie with ID '{request.movie_id}' was not found"
            )

        cinema = await self.cinema_repository.find_by_id(
            CinemaId(value=request.cinema_id)
        )
        if cinema is None:
            raise CinemaNotFoundError(
                f"A cinema with ID '{request.cinema_id}' was not found"
            )

        screening = Screening(
            id=ScreeningId(value=str(uuid4())),
            movie=movie,
            cinema=cinema,
            showtime=Showtime(value=request.showtime),
            external_id=request.external_id,
            ticket_url=request.ticket_url,
            room=request.room,
            language=request.language,
        )
        saved = await self.screening_repository.save(screening)

        return self.OutputData(
            id=str(saved.id),
            movie_id=str(saved.movie.id),
            movie_title=saved.movie.title,
            cinema_id=str(saved.cinema.id),
            cinema_name=saved.cinema.name,
            showtime=saved.showtime.value,
            ticket_url=saved.ticket_url,
            room=saved.room,
            language=saved.language,
        )
