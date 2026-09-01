"""Partially update screening use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.repositories import ScreeningRepository
from marquise.application.use_cases._screening_helpers import (
    reject_blank_when_provided,
    require_non_empty,
    screening_output_data,
)
from marquise.domain.entities import Screening
from marquise.domain.value_objects import ScreeningId


class PatchScreeningUseCase:
    """Use case for partially updating a screening.

    Identity fields (movie, cinema, showtime) cannot be changed through
    this use case. Omitted optional fields are left unchanged.
    """

    @dataclass(frozen=True, slots=True)
    class InputData:
        """Input data for a partial screening update.

        Attributes:
            screening_id: Unique identifier of the screening to update.
            ticket_url: Replacement ticket URL, or None to leave unchanged.
            room: Replacement room name, or None to leave unchanged.
            language: Replacement language, or None to leave unchanged.
            external_id: Replacement source identifier, or None to leave
                unchanged.
        """

        screening_id: str
        ticket_url: str | None = None
        room: str | None = None
        language: str | None = None
        external_id: str | None = None

        def __post_init__(self) -> None:
            """Validate input data.

            Raises:
                ValueError: If screening_id is empty, or optional strings
                    are provided but whitespace-only.
            """
            require_non_empty(self.screening_id, "screening_id")
            reject_blank_when_provided(self.ticket_url, "ticket_url")
            reject_blank_when_provided(self.room, "room")
            reject_blank_when_provided(self.language, "language")
            reject_blank_when_provided(self.external_id, "external_id")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        """Output data returned after a successful partial update.

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

    def __init__(self, screening_repository: ScreeningRepository) -> None:
        """Initialize the use case.

        Args:
            screening_repository: A repository for screening persistence.
        """
        self.screening_repository = screening_repository

    async def execute(self, request: InputData) -> OutputData:
        """Partially update an existing screening.

        Loads the screening by ID and updates only the optional fields
        provided on the request. Identity fields are taken from the
        existing record.

        Args:
            request: The input data for the partial update.

        Returns:
            The output data containing the updated screening details.

        Raises:
            ScreeningNotFoundError: If no screening with the given ID exists.
        """
        existing = await self.screening_repository.find_by_id(
            ScreeningId(value=request.screening_id)
        )
        updated = await self.screening_repository.update(
            Screening(
                id=existing.id,
                movie=existing.movie,
                cinema=existing.cinema,
                showtime=existing.showtime,
                external_id=(
                    request.external_id
                    if request.external_id is not None
                    else existing.external_id
                ),
                ticket_url=(
                    request.ticket_url
                    if request.ticket_url is not None
                    else existing.ticket_url
                ),
                room=request.room if request.room is not None else existing.room,
                language=(
                    request.language
                    if request.language is not None
                    else existing.language
                ),
            )
        )
        if updated is None:
            raise ScreeningNotFoundError(
                f"A screening with ID '{request.screening_id}' was not found"
            )

        return screening_output_data(self.OutputData, updated)
