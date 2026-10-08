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
    proposed = replace(saved, room="outdated")
    with pytest.raises(ScreeningWriteConflictError):
        await repository.commit_import(proposed, incoming=incoming, expected=state)
    assert (await repository.find_by_id(saved.id)).room == "concurrently changed"
    with pytest.raises(ScreeningWriteConflictError):
        await repository.commit_import(incoming, incoming=incoming, expected=())
    moved = replace(
        changed, showtime=Showtime(changed.showtime.value + timedelta(minutes=15))
    )
    state = await repository.read_import_candidates(moved)
    result = await repository.commit_import(moved, incoming=moved, expected=state)
    assert result.id == saved.id
    assert result.showtime == moved.showtime


async def assert_target_arrival(
    repository: ScreeningRepository, original: Screening
) -> None:
    """An occupied target arriving after the snapshot cannot be overwritten."""
    await repository.commit_import(original, incoming=original, expected=())
    incoming = replace(
        original, showtime=Showtime(original.showtime.value + timedelta(minutes=15))
    )
    state = await repository.read_import_candidates(incoming)
    target = replace(
        incoming, id=type(original.id)("target"), external_id=None, room="unrelated"
    )
    await repository.commit_import(target, incoming=target, expected=())
    with pytest.raises(ScreeningWriteConflictError):
        await repository.commit_import(incoming, incoming=incoming, expected=state)
    assert await repository.find_by_id(original.id) == original
    assert await repository.find_by_id(target.id) == target


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
