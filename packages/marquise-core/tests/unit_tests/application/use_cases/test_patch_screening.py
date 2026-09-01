"""Tests for PatchScreeningUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import ScreeningNotFoundError
from marquise.application.repositories import ScreeningRepository
from marquise.application.use_cases.patch_screening import PatchScreeningUseCase
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime

SHOWTIME = datetime(2026, 6, 27, 19, 30, tzinfo=UTC)


def _existing() -> Screening:
    return Screening(
        id=ScreeningId(value="scr-1"),
        movie=Movie(id=MovieId(value="mov-1"), title="The Odyssey"),
        cinema=Cinema(id=CinemaId(value="cin-1"), name="Cinema One"),
        showtime=Showtime(value=SHOWTIME),
        ticket_url="https://old.example/t",
        room="Salle 1",
        language="V.F.",
        external_id="ext-1",
    )


def _patched() -> Screening:
    existing = _existing()
    return Screening(
        id=existing.id,
        movie=existing.movie,
        cinema=existing.cinema,
        showtime=existing.showtime,
        ticket_url="https://new.example/t",
        room=existing.room,
        language=existing.language,
        external_id=existing.external_id,
    )


@pytest.mark.asyncio
async def test_patches_provided_fields_and_keeps_identity() -> None:
    """PATCH updates optional fields and leaves movie, cinema, and showtime."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.find_by_id.return_value = _existing()
    screening_repo.update.return_value = _patched()
    use_case = PatchScreeningUseCase(screening_repository=screening_repo)

    result = await use_case.execute(
        PatchScreeningUseCase.InputData(
            screening_id="scr-1",
            ticket_url="https://new.example/t",
        )
    )

    assert result.id == "scr-1"
    assert result.movie_id == "mov-1"
    assert result.cinema_id == "cin-1"
    assert result.showtime == SHOWTIME
    assert result.ticket_url == "https://new.example/t"
    assert result.room == "Salle 1"
    screening_repo.find_by_id.assert_awaited_once_with(ScreeningId(value="scr-1"))
    screening_repo.update.assert_awaited_once()
    submitted = screening_repo.update.await_args.args[0]
    assert submitted.movie.id == MovieId(value="mov-1")
    assert submitted.cinema.id == CinemaId(value="cin-1")
    assert submitted.showtime.value == SHOWTIME
    assert submitted.ticket_url == "https://new.example/t"
    assert submitted.room is None
    assert submitted.language is None
    assert submitted.external_id is None


@pytest.mark.asyncio
async def test_raises_when_screening_missing() -> None:
    """PATCH of an unknown screening raises ScreeningNotFoundError."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.find_by_id.side_effect = ScreeningNotFoundError(
        "A screening with ID 'missing' was not found"
    )
    use_case = PatchScreeningUseCase(screening_repository=screening_repo)

    with pytest.raises(ScreeningNotFoundError, match="missing"):
        await use_case.execute(PatchScreeningUseCase.InputData(screening_id="missing"))

    screening_repo.update.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_update_finds_no_row() -> None:
    """A concurrent delete during PATCH raises ScreeningNotFoundError."""
    screening_repo = create_autospec(ScreeningRepository, instance=True)
    screening_repo.find_by_id.return_value = _existing()
    screening_repo.update.return_value = None
    use_case = PatchScreeningUseCase(screening_repository=screening_repo)

    with pytest.raises(ScreeningNotFoundError, match="scr-1"):
        await use_case.execute(
            PatchScreeningUseCase.InputData(screening_id="scr-1", room="Salle 2")
        )


def test_input_rejects_empty_screening_id() -> None:
    """An empty screening_id is rejected."""
    with pytest.raises(ValueError, match="screening_id must not be empty"):
        PatchScreeningUseCase.InputData(screening_id="  ")


def test_input_rejects_blank_optionals_when_provided() -> None:
    """Provided optional strings must not be whitespace-only."""
    with pytest.raises(ValueError, match="ticket_url must not be empty when provided"):
        PatchScreeningUseCase.InputData(screening_id="scr-1", ticket_url="")
    with pytest.raises(ValueError, match="room must not be empty when provided"):
        PatchScreeningUseCase.InputData(screening_id="scr-1", room=" ")
    with pytest.raises(ValueError, match="language must not be empty when provided"):
        PatchScreeningUseCase.InputData(screening_id="scr-1", language="")
    with pytest.raises(ValueError, match="external_id must not be empty when provided"):
        PatchScreeningUseCase.InputData(screening_id="scr-1", external_id="  ")
