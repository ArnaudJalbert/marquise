"""Tests for UpdateScreeningUseCase."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    CinemaNotFoundError,
    MovieNotFoundError,
    ScreeningAlreadyExistsError,
    ScreeningNotFoundError,
)
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    ScreeningRepository,
)
from marquise.application.use_cases._screening_helpers import UNSET
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime

OLD_SHOWTIME = datetime(2026, 6, 27, 19, 30, tzinfo=UTC)
NEW_SHOWTIME = datetime(2026, 6, 28, 21, 0, tzinfo=UTC)


@pytest.fixture
def existing() -> Screening:
    """Provide the screening currently stored for update tests."""
    return Screening(
        id=ScreeningId(value="scr-1"),
        movie=Movie(id=MovieId(value="mov-1"), title="The Odyssey"),
        cinema=Cinema(id=CinemaId(value="cin-1"), name="Cinema One"),
        showtime=Showtime(value=OLD_SHOWTIME),
        ticket_url="https://old.example/t",
        room="Salle 1",
        language="V.F.",
        external_id="ext-1",
    )


@pytest.fixture
def replacement_movie() -> Movie:
    """Provide a replacement movie for identity updates."""
    return Movie(id=MovieId(value="mov-2"), title="Dune")


@pytest.fixture
def replacement_cinema() -> Cinema:
    """Provide a replacement cinema for identity updates."""
    return Cinema(id=CinemaId(value="cin-2"), name="Cinema Two")


@pytest.fixture
def screening_repository(existing: Screening) -> ScreeningRepository:
    """Provide an autospecced screening repository loaded with the existing row."""
    repository = create_autospec(ScreeningRepository, instance=True)
    repository.find_by_id.return_value = existing
    repository.replace.return_value = existing
    return repository


@pytest.fixture
def movie_repository(replacement_movie: Movie) -> MovieRepository:
    """Provide an autospecced movie repository that finds the replacement movie."""
    repository = create_autospec(MovieRepository, instance=True)
    repository.find_by_id.return_value = replacement_movie
    return repository


@pytest.fixture
def cinema_repository(replacement_cinema: Cinema) -> CinemaRepository:
    """Provide an autospecced cinema repository that finds the replacement cinema."""
    repository = create_autospec(CinemaRepository, instance=True)
    repository.find_by_id.return_value = replacement_cinema
    return repository


@pytest.fixture
def use_case(
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
    cinema_repository: CinemaRepository,
) -> UpdateScreeningUseCase:
    """Provide a configured update-screening use case."""
    return UpdateScreeningUseCase(
        screening_repository=screening_repository,
        movie_repository=movie_repository,
        cinema_repository=cinema_repository,
    )


@pytest.mark.asyncio
async def test_updates_only_provided_metadata_fields(
    use_case: UpdateScreeningUseCase,
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
    cinema_repository: CinemaRepository,
    existing: Screening,
) -> None:
    """A partial update changes only the fields sent on the request."""
    screening_repository.replace.return_value = Screening(
        id=existing.id,
        movie=existing.movie,
        cinema=existing.cinema,
        showtime=existing.showtime,
        ticket_url="https://new.example/t",
        room=existing.room,
        language=existing.language,
        external_id=existing.external_id,
    )

    result = await use_case.execute(
        UpdateScreeningUseCase.InputData(
            screening_id="scr-1",
            ticket_url="https://new.example/t",
        )
    )

    assert result.ticket_url == "https://new.example/t"
    assert result.movie_id == "mov-1"
    assert result.showtime == OLD_SHOWTIME
    movie_repository.find_by_id.assert_not_awaited()
    cinema_repository.find_by_id.assert_not_awaited()
    submitted = screening_repository.replace.await_args.args[0]
    assert submitted.ticket_url == "https://new.example/t"
    assert submitted.room == "Salle 1"
    assert submitted.external_id == "ext-1"


@pytest.mark.asyncio
async def test_updates_all_fields_when_provided(
    use_case: UpdateScreeningUseCase,
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
    cinema_repository: CinemaRepository,
    replacement_movie: Movie,
    replacement_cinema: Cinema,
) -> None:
    """A full update can replace identity and optional fields."""
    screening_repository.replace.return_value = Screening(
        id=ScreeningId(value="scr-1"),
        movie=replacement_movie,
        cinema=replacement_cinema,
        showtime=Showtime(value=NEW_SHOWTIME),
        ticket_url=None,
        room="Salle 9",
        language="V.O.",
        external_id=None,
    )

    result = await use_case.execute(
        UpdateScreeningUseCase.InputData(
            screening_id="scr-1",
            movie_id="mov-2",
            cinema_id="cin-2",
            showtime=NEW_SHOWTIME,
            ticket_url=None,
            room="Salle 9",
            language="V.O.",
            external_id=None,
        )
    )

    assert result.movie_id == "mov-2"
    assert result.cinema_id == "cin-2"
    assert result.showtime == NEW_SHOWTIME
    assert result.ticket_url is None
    movie_repository.find_by_id.assert_awaited_once_with(MovieId(value="mov-2"))
    cinema_repository.find_by_id.assert_awaited_once_with(CinemaId(value="cin-2"))


@pytest.mark.asyncio
async def test_clears_optional_field_when_explicitly_set_to_none(
    use_case: UpdateScreeningUseCase,
    screening_repository: ScreeningRepository,
    existing: Screening,
) -> None:
    """Explicit None clears optional metadata fields."""
    screening_repository.replace.return_value = Screening(
        id=existing.id,
        movie=existing.movie,
        cinema=existing.cinema,
        showtime=existing.showtime,
        ticket_url=None,
        room=None,
        language=None,
        external_id=None,
    )

    result = await use_case.execute(
        UpdateScreeningUseCase.InputData(
            screening_id="scr-1",
            ticket_url=None,
            room=None,
            language=None,
            external_id=None,
        )
    )

    submitted = screening_repository.replace.await_args.args[0]
    assert submitted.ticket_url is None
    assert submitted.room is None
    assert submitted.language is None
    assert submitted.external_id is None
    assert screening_repository.replace.await_args.kwargs["fields"] == frozenset(
        {"ticket_url", "room", "language", "external_id"}
    )
    assert result.ticket_url is None
    assert result.room is None
    assert result.language is None


@pytest.mark.asyncio
async def test_reuses_existing_parents_when_identity_unchanged(
    use_case: UpdateScreeningUseCase,
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
    cinema_repository: CinemaRepository,
) -> None:
    """Unchanged movie and cinema IDs do not trigger extra lookups."""
    await use_case.execute(
        UpdateScreeningUseCase.InputData(
            screening_id="scr-1",
            movie_id="mov-1",
            cinema_id="cin-1",
            showtime=NEW_SHOWTIME,
        )
    )

    movie_repository.find_by_id.assert_not_awaited()
    cinema_repository.find_by_id.assert_not_awaited()
    submitted = screening_repository.replace.await_args.args[0]
    assert submitted.movie.title == "The Odyssey"
    assert submitted.cinema.name == "Cinema One"


@pytest.mark.asyncio
async def test_raises_when_screening_missing(
    use_case: UpdateScreeningUseCase,
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
    cinema_repository: CinemaRepository,
) -> None:
    """Updating an unknown screening raises ScreeningNotFoundError."""
    screening_repository.find_by_id.side_effect = ScreeningNotFoundError(
        "A screening with ID 'missing' was not found"
    )

    with pytest.raises(ScreeningNotFoundError, match="missing"):
        await use_case.execute(
            UpdateScreeningUseCase.InputData(screening_id="missing", room="Salle 2")
        )

    movie_repository.find_by_id.assert_not_awaited()
    cinema_repository.find_by_id.assert_not_awaited()
    screening_repository.replace.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_movie_missing(
    use_case: UpdateScreeningUseCase,
    screening_repository: ScreeningRepository,
    movie_repository: MovieRepository,
) -> None:
    """Unknown replacement movie IDs are rejected before persist."""
    movie_repository.find_by_id.return_value = None

    with pytest.raises(MovieNotFoundError, match="mov-2"):
        await use_case.execute(
            UpdateScreeningUseCase.InputData(screening_id="scr-1", movie_id="mov-2")
        )

    screening_repository.replace.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_cinema_missing(
    use_case: UpdateScreeningUseCase,
    screening_repository: ScreeningRepository,
    cinema_repository: CinemaRepository,
) -> None:
    """Unknown replacement cinema IDs are rejected before persist."""
    cinema_repository.find_by_id.return_value = None

    with pytest.raises(CinemaNotFoundError, match="cin-2"):
        await use_case.execute(
            UpdateScreeningUseCase.InputData(screening_id="scr-1", cinema_id="cin-2")
        )

    screening_repository.replace.assert_not_awaited()


@pytest.mark.asyncio
async def test_raises_when_update_conflicts(
    use_case: UpdateScreeningUseCase,
    screening_repository: ScreeningRepository,
) -> None:
    """A unique-constraint conflict surfaces ScreeningAlreadyExistsError."""
    screening_repository.replace.side_effect = ScreeningAlreadyExistsError(
        "already exists"
    )

    with pytest.raises(ScreeningAlreadyExistsError, match="already exists"):
        await use_case.execute(
            UpdateScreeningUseCase.InputData(
                screening_id="scr-1",
                showtime=NEW_SHOWTIME,
            )
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("first_field", ["room", "movie_id"])
async def test_concurrent_partial_updates_preserve_omitted_fields(
    use_case: UpdateScreeningUseCase,
    screening_repository: ScreeningRepository,
    existing: Screening,
    replacement_movie: Movie,
    first_field: str,
) -> None:
    """Requests reading the same snapshot do not overwrite each other's changes."""
    snapshots_read = asyncio.Event()
    first_written = asyncio.Event()
    reads = 0
    stored = existing

    async def read_snapshot(screening_id: ScreeningId) -> Screening:
        nonlocal reads
        reads += 1
        if reads == 2:
            snapshots_read.set()
        await snapshots_read.wait()
        return existing

    async def write_fields(
        screening: Screening, *, fields: frozenset[str] | None = None
    ) -> Screening:
        nonlocal stored
        if screening.language == "V.O.":
            await first_written.wait()
        if fields is None:
            stored = screening
        else:
            names = {"movie_id": "movie", "cinema_id": "cinema"}
            stored = replace(
                stored,
                **{
                    names.get(name, name): getattr(screening, names.get(name, name))
                    for name in fields
                },
            )
        first_written.set()
        return stored

    screening_repository.find_by_id.side_effect = read_snapshot
    screening_repository.replace.side_effect = write_fields
    first_request = (
        UpdateScreeningUseCase.InputData(screening_id="scr-1", room=None)
        if first_field == "room"
        else UpdateScreeningUseCase.InputData(screening_id="scr-1", movie_id="mov-2")
    )

    _, second_result = await asyncio.wait_for(
        asyncio.gather(
            use_case.execute(first_request),
            use_case.execute(
                UpdateScreeningUseCase.InputData(screening_id="scr-1", language="V.O.")
            ),
        ),
        timeout=2,
    )

    assert stored.language == "V.O."
    if first_field == "room":
        assert stored.room is None
        assert second_result.room is None
    else:
        assert stored.movie == replacement_movie
        assert second_result.movie_id == "mov-2"
        assert second_result.movie_title == "Dune"
    assert {
        call.kwargs["fields"] for call in screening_repository.replace.await_args_list
    } == {frozenset({first_field}), frozenset({"language"})}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("request_fields", "expected"),
    [
        ({}, frozenset()),
        ({"ticket_url": None}, frozenset({"ticket_url"})),
        (
            {"movie_id": "mov-1", "cinema_id": "cin-1"},
            frozenset({"movie_id", "cinema_id"}),
        ),
    ],
)
async def test_update_masks_explicit_fields_even_when_unchanged(
    use_case: UpdateScreeningUseCase,
    screening_repository: ScreeningRepository,
    request_fields: dict,
    expected: frozenset[str],
) -> None:
    """Omission, explicit clears, and explicitly unchanged IDs retain their intent."""
    await use_case.execute(
        UpdateScreeningUseCase.InputData(screening_id="scr-1", **request_fields)
    )
    assert screening_repository.replace.await_args.kwargs == {"fields": expected}


def test_input_rejects_empty_screening_id() -> None:
    """An empty screening_id is rejected."""
    with pytest.raises(ValueError, match="screening_id must not be empty"):
        UpdateScreeningUseCase.InputData(screening_id="  ")


def test_input_rejects_empty_identity_fields_when_provided() -> None:
    """Provided identity fields must not be empty."""
    with pytest.raises(ValueError, match="movie_id must not be empty"):
        UpdateScreeningUseCase.InputData(screening_id="scr-1", movie_id="")
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        UpdateScreeningUseCase.InputData(screening_id="scr-1", cinema_id="  ")


def test_input_rejects_naive_showtime_when_provided() -> None:
    """Naive showtimes are rejected when showtime is provided."""
    with pytest.raises(ValueError, match="showtime must be timezone-aware"):
        UpdateScreeningUseCase.InputData(
            screening_id="scr-1",
            showtime=datetime(2026, 6, 28, 21, 0),
        )


def test_input_rejects_blank_optionals_when_provided() -> None:
    """Provided optional strings must not be whitespace-only."""
    with pytest.raises(ValueError, match="ticket_url must not be empty when provided"):
        UpdateScreeningUseCase.InputData(screening_id="scr-1", ticket_url="")
    with pytest.raises(ValueError, match="room must not be empty when provided"):
        UpdateScreeningUseCase.InputData(screening_id="scr-1", room=" ")
    with pytest.raises(ValueError, match="language must not be empty when provided"):
        UpdateScreeningUseCase.InputData(screening_id="scr-1", language="")
    with pytest.raises(ValueError, match="external_id must not be empty when provided"):
        UpdateScreeningUseCase.InputData(screening_id="scr-1", external_id="  ")


def test_unset_fields_remain_distinct_from_explicit_none() -> None:
    """UNSET means omit; None means clear for optional metadata."""
    omitted = UpdateScreeningUseCase.InputData(screening_id="scr-1")
    cleared = UpdateScreeningUseCase.InputData(screening_id="scr-1", ticket_url=None)

    assert omitted.ticket_url is UNSET
    assert cleared.ticket_url is None
