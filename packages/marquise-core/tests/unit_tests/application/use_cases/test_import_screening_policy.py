"""Import behavior with storage that has no reschedule eligibility rules."""

from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import create_autospec
from zoneinfo import ZoneInfo

import pytest

from marquise.application.exceptions.screening import (
    ScreeningImportRetryExhaustedError,
    ScreeningWriteConflictError,
)
from marquise.application.repositories import ScreeningRepository
from marquise.domain.entities import Cinema, Movie
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime
from support.screening_import import owner, run_import
from support.screening_memory import MemoryScreeningRepository


@pytest.mark.asyncio
async def test_same_day_move_preserves_id_metadata_and_reimports() -> None:
    """A correction moves the original ID once and a repeat only updates metadata."""
    original = owner()
    repository = MemoryScreeningRepository((original,))
    incoming = replace(
        original,
        showtime=Showtime(datetime(2026, 10, 7, 17, 15, tzinfo=UTC)),
        room="new",
    )
    result = await run_import(repository, incoming)
    assert result.rescheduled_count == 1
    assert result.imported_count == result.updated_count == result.skipped_count == 0
    assert tuple(repository.rows) == (original.id,)
    assert repository.rows[original.id] == incoming
    repeated = await run_import(repository, incoming)
    assert repeated.rescheduled_count == repeated.imported_count == 0
    assert repeated.updated_count == 1


@pytest.mark.asyncio
async def test_removed_owner_is_skipped_after_stale_write() -> None:
    """A concurrent deletion cannot recreate a correction with a new ID."""
    original = owner()
    repository = MemoryScreeningRepository((original,))
    repository.before_commit = lambda: repository.rows.clear()
    incoming = replace(
        original, showtime=Showtime(datetime(2026, 10, 7, 17, 15, tzinfo=UTC))
    )
    result = await run_import(repository, incoming)
    assert result.skipped_count == 1
    assert result.imported_count == result.rescheduled_count == 0
    assert repository.rows == {}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "reason", ["unknown", "source", "movie", "occupied", "ambiguous"]
)
async def test_refused_corrections_preserve_all_rows(reason: str) -> None:
    """Unverified ownership, reused IDs and colliding identities are never merged."""
    original = owner()
    incoming = replace(
        original, showtime=Showtime(datetime(2026, 10, 7, 17, 15, tzinfo=UTC))
    )
    rows = (original,)
    if reason == "unknown":
        rows = (replace(original, source_name=None),)
    elif reason == "source":
        rows = (replace(original, source_name="other"),)
    elif reason == "movie":
        incoming = replace(
            incoming, movie=Movie(id=MovieId("other"), title="Other film")
        )
    elif reason == "occupied":
        rows += (replace(incoming, id=ScreeningId("target"), external_id=None),)
    elif reason == "ambiguous":
        rows += (
            replace(
                original,
                id=ScreeningId("ambiguous"),
                showtime=Showtime(datetime(2026, 10, 7, 18, tzinfo=UTC)),
            ),
        )
    repository = MemoryScreeningRepository(rows)
    before = repository.rows.copy()
    result = await run_import(repository, incoming)
    assert result.skipped_count == 1
    assert result.total_count == result.imported_count == result.rescheduled_count == 0
    assert repository.rows == before


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("old", "new", "accepted"),
    [
        ("2026-03-08T00:30", "2026-03-08T23:30", True),
        ("2026-03-09T00:30", "2026-03-08T18:00", False),
        ("2026-11-01T00:30", "2026-11-01T23:30", True),
        ("2026-10-08T00:00", "2026-10-07T23:59", False),
        ("2026-10-06T23:59", "2026-10-07T00:00", False),
    ],
)
async def test_montreal_calendar_day_boundaries(
    old: str, new: str, accepted: bool
) -> None:
    """Midnight and DST days use Montreal dates rather than 24-hour intervals."""
    zone = ZoneInfo("America/Montreal")
    original = replace(
        owner(), showtime=Showtime(datetime.fromisoformat(old).replace(tzinfo=zone))
    )
    incoming = replace(
        original, showtime=Showtime(datetime.fromisoformat(new).replace(tzinfo=zone))
    )
    repository = MemoryScreeningRepository((original,))
    result = await run_import(repository, incoming)
    assert result.rescheduled_count == int(accepted)
    assert result.skipped_count == int(not accepted)
    assert repository.rows[original.id].showtime == (
        incoming.showtime if accepted else original.showtime
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("external_id", [None, ""])
async def test_idless_updates_preserve_unknown_provenance(
    external_id: str | None,
) -> None:
    """Metadata without a native ID cannot attest the retained historical key."""
    original = replace(owner(), source_name=None)
    repository = MemoryScreeningRepository((original,))
    incoming = replace(
        original, external_id=external_id, source_name="cineplex", room="new"
    )
    result = await run_import(repository, incoming)
    assert result.updated_count == 1
    observed = repository.rows[original.id]
    assert observed.external_id == "native"
    assert observed.source_name is None
    assert observed.room == "new"
    correction = replace(
        owner(), showtime=Showtime(datetime(2026, 10, 7, 17, 15, tzinfo=UTC))
    )
    assert (await run_import(repository, correction)).skipped_count == 1
    assert repository.rows[original.id] == observed


@pytest.mark.asyncio
@pytest.mark.parametrize("external_id", [None, "", "different"])
async def test_unmatched_native_id_creates_new_performance(
    external_id: str | None,
) -> None:
    """Missing or different keys create a new performance."""
    original = owner()
    repository = MemoryScreeningRepository((original,))
    incoming = replace(
        original,
        external_id=external_id,
        showtime=Showtime(datetime(2026, 10, 7, 18, tzinfo=UTC)),
    )
    result = await run_import(repository, incoming)
    assert result.imported_count == 1
    assert result.rescheduled_count == 0
    assert len(repository.rows) == 2
    assert repository.rows[original.id] == original


@pytest.mark.asyncio
async def test_native_ids_are_scoped_to_cinema() -> None:
    """Another Cinema can reuse the native ID without moving the original."""
    original = owner()
    repository = MemoryScreeningRepository((original,))
    incoming = replace(
        original, cinema=Cinema(id=CinemaId("other"), name="Other Cinema")
    )
    result = await run_import(repository, incoming)
    assert result.imported_count == 1
    assert result.rescheduled_count == 0
    assert repository.rows[original.id] == original


@pytest.mark.asyncio
async def test_metadata_cannot_take_over_another_source() -> None:
    """A same-time observation cannot relabel another provider's native ownership."""
    original = replace(owner(), source_name="other")
    repository = MemoryScreeningRepository((original,))
    result = await run_import(
        repository, replace(original, source_name="cineplex", room="new")
    )
    assert result.skipped_count == 1
    assert repository.rows[original.id] == original


@pytest.mark.asyncio
async def test_dst_fold_batch_is_refused() -> None:
    """Repeated clock readings denote distinct performances sharing one native ID."""
    original = owner()
    zone = ZoneInfo("America/Montreal")
    first = replace(
        original, showtime=Showtime(datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0))
    )
    second = replace(first, showtime=Showtime(first.showtime.value.replace(fold=1)))
    repository = MemoryScreeningRepository((original,))
    result = await run_import(repository, first, second)
    assert result.skipped_count == 2
    assert repository.rows == {original.id: original}


@pytest.mark.asyncio
async def test_stale_source_change_is_reevaluated() -> None:
    """A source changed between read and commit refuses the outdated correction."""
    original = owner()
    repository = MemoryScreeningRepository((original,))
    repository.before_commit = lambda: repository.rows.update(
        {original.id: replace(original, source_name="other")}
    )
    incoming = replace(
        original, showtime=Showtime(datetime(2026, 10, 7, 17, 15, tzinfo=UTC))
    )
    result = await run_import(repository, incoming)
    assert result.skipped_count == 1
    assert repository.rows[original.id].source_name == "other"
    assert repository.rows[original.id].showtime == original.showtime


@pytest.mark.asyncio
async def test_retry_exhaustion_is_explicit() -> None:
    """Repeated stale writes exhaust bounded attempts and fail explicitly."""
    repository = create_autospec(ScreeningRepository, instance=True)
    repository.read_import_candidates.return_value = (owner(),)
    repository.commit_import.side_effect = ScreeningWriteConflictError("changed")
    with pytest.raises(
        ScreeningImportRetryExhaustedError, match="3 checked-write attempts"
    ):
        await run_import(
            repository,
            replace(owner(), showtime=Showtime(datetime(2026, 10, 7, 18, tzinfo=UTC))),
        )
    assert repository.commit_import.await_count == 3


@pytest.mark.asyncio
async def test_five_historical_corrections_preserve_ids_and_counts() -> None:
    """The five verified October 7 corrections move once without duplicates."""
    observed = (
        (
            "a297eb7aee024c8a80fd84ceeab2de7d",
            "597122",
            "digger",
            "DIGGER",
            "13:00",
            "13:15",
        ),
        (
            "cdc597ed360c4d1aac255dd4ea31ab7c",
            "597137",
            "digger",
            "DIGGER",
            "15:55",
            "16:10",
        ),
        (
            "d597fb40a95d43d6baea3e2cf790db48",
            "597142",
            "parents",
            "Chers Parents",
            "14:00",
            "14:05",
        ),
        (
            "af6e45e97653455dbbac56047f28c5b1",
            "597152",
            "parents",
            "Chers Parents",
            "16:20",
            "16:25",
        ),
        (
            "62db2eac23d24e48b0dfa9df86c38f08",
            "597161",
            "parents",
            "Chers Parents",
            "18:30",
            "18:35",
        ),
    )
    zone = ZoneInfo("America/Montreal")
    originals = tuple(
        replace(
            owner(),
            id=ScreeningId(identifier),
            external_id=native,
            movie=Movie(id=MovieId(movie), title=title),
            showtime=Showtime(
                datetime.fromisoformat("2026-10-07T" + old).replace(tzinfo=zone)
            ),
        )
        for identifier, native, movie, title, old, new in observed
    )
    incoming = tuple(
        replace(
            original,
            showtime=Showtime(
                datetime.fromisoformat("2026-10-07T" + values[5]).replace(tzinfo=zone)
            ),
            room="corrected",
        )
        for original, values in zip(originals, observed, strict=True)
    )
    repository = MemoryScreeningRepository(originals)
    result = await run_import(repository, *incoming)
    assert result.rescheduled_count == 5
    assert result.imported_count == result.updated_count == result.skipped_count == 0
    assert repository.rows == {row.id: row for row in incoming}
    repeated = await run_import(repository, *incoming)
    assert repeated.updated_count == 5
    assert (
        repeated.imported_count
        == repeated.rescheduled_count
        == repeated.skipped_count
        == 0
    )


@pytest.mark.asyncio
async def test_target_arrival_is_reloaded_and_refused() -> None:
    """A target committed after the read is neither overwritten nor merged."""
    original = owner()
    incoming = replace(
        original, showtime=Showtime(datetime(2026, 10, 7, 18, tzinfo=UTC))
    )
    target = replace(
        incoming, id=ScreeningId("target"), external_id=None, room="unrelated"
    )
    repository = MemoryScreeningRepository((original,))
    repository.before_commit = lambda: repository.rows.update({target.id: target})
    result = await run_import(repository, incoming)
    assert result.skipped_count == 1
    assert repository.rows == {original.id: original, target.id: target}


@pytest.mark.asyncio
async def test_stale_metadata_is_reloaded_and_preserved() -> None:
    """Retrying a correction retains metadata committed after the initial read."""
    original = owner()
    incoming = replace(
        original, showtime=Showtime(datetime(2026, 10, 7, 18, tzinfo=UTC)), room=None
    )
    concurrent = replace(original, room="concurrent")
    repository = MemoryScreeningRepository((original,))
    repository.before_commit = lambda: repository.rows.update({original.id: concurrent})
    result = await run_import(repository, incoming)
    assert result.rescheduled_count == 1
    assert repository.rows[original.id].room == "concurrent"
