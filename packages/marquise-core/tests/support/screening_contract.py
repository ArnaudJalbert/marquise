"""Behavioral contract shared by Screening persistence implementations."""

from dataclasses import replace
from datetime import timedelta

import pytest

from marquise.application.exceptions.screening import ScreeningWriteConflictError
from marquise.application.repositories import ScreeningRepository
from marquise.domain.entities import Screening
from marquise.domain.value_objects import Showtime


async def assert_checked_writes(
    repository: ScreeningRepository, incoming: Screening
) -> None:
    """Stale snapshots and arrived targets cannot overwrite a checked row."""
    assert await repository.read_import_candidates(incoming) == ()
    saved = await repository.commit_import(incoming, incoming=incoming, expected=())
    state = await repository.read_import_candidates(incoming)
    changed = replace(saved, room="concurrently changed")
    await repository.commit_import(changed, incoming=incoming, expected=state)
    await assert_stale_snapshot_rejected(repository, incoming, state)
    await assert_candidate_room(repository, incoming, "concurrently changed")
    await assert_incoming_write_rejected(repository, incoming)
    await assert_move_preserves_identity(repository, saved, changed)


async def assert_stale_snapshot_rejected(
    repository: ScreeningRepository,
    incoming: Screening,
    state: tuple[Screening, ...],
) -> None:
    """A stale snapshot cannot overwrite a concurrent update."""
    proposed = replace(incoming, room="outdated")
    with pytest.raises(ScreeningWriteConflictError):
        await repository.commit_import(proposed, incoming=incoming, expected=state)


async def assert_candidate_room(
    repository: ScreeningRepository, incoming: Screening, room: str
) -> None:
    """The current candidate keeps its latest room."""
    candidates = await repository.read_import_candidates(incoming)
    assert len(candidates) == 1
    assert candidates[0].room == room


async def assert_incoming_write_rejected(
    repository: ScreeningRepository, incoming: Screening
) -> None:
    """An empty expected snapshot cannot overwrite an existing screening."""
    with pytest.raises(ScreeningWriteConflictError):
        await repository.commit_import(incoming, incoming=incoming, expected=())


async def assert_move_preserves_identity(
    repository: ScreeningRepository, saved: Screening, changed: Screening
) -> None:
    """A moved screening keeps its persisted identity."""
    moved = move_by_15_minutes(changed)
    state = await repository.read_import_candidates(moved)
    result = await repository.commit_import(moved, incoming=moved, expected=state)
    assert result.id == saved.id
    assert result.showtime == moved.showtime


def move_by_15_minutes(screening: Screening) -> Screening:
    return replace(
        screening,
        showtime=Showtime(screening.showtime.value + timedelta(minutes=15)),
    )


async def assert_target_arrival(
    repository: ScreeningRepository, original: Screening
) -> None:
    """An occupied target arriving after the snapshot cannot be overwritten."""
    await repository.commit_import(original, incoming=original, expected=())
    incoming = move_by_15_minutes(original)
    state = await repository.read_import_candidates(incoming)
    target = build_target_screening(incoming)
    await repository.commit_import(target, incoming=target, expected=())
    await assert_stale_snapshot_rejected(repository, incoming, state)
    await assert_candidates_equal(repository, original, (original,))
    await assert_candidates_equal(repository, target, (target,))


def build_target_screening(incoming: Screening) -> Screening:
    return replace(
        incoming,
        id=type(incoming.id)("target"),
        external_id=None,
        room="unrelated",
    )


async def assert_candidates_equal(
    repository: ScreeningRepository,
    incoming: Screening,
    expected: tuple[Screening, ...],
) -> None:
    """Candidate lookup returns the expected entities."""
    assert await repository.read_import_candidates(incoming) == expected


async def assert_removed_owner(
    repository: ScreeningRepository, original: Screening
) -> None:
    """A snapshot of a deleted row cannot authorize an insert or overwrite."""
    await repository.commit_import(original, incoming=original, expected=())
    state = await repository.read_import_candidates(original)
    await repository.delete(original.id)
    with pytest.raises(ScreeningWriteConflictError):
        await repository.commit_import(original, incoming=original, expected=state)
    assert await repository.read_import_candidates(original) == ()
