"""Audited writes through the technology-agnostic application interface."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import MagicMock, create_autospec

import pytest

from marquise.application.exceptions import ScreeningIdempotencyConflictError
from marquise.application.repositories import MovieRepository, ScreeningRepository
from marquise.application.transactions.screening_write import (
    ScreeningWriteResult,
    ScreeningWriteTransaction,
)
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.application.use_cases.write_screening import (
    WriteScreeningUseCase,
)
from marquise.domain.entities import Cinema, Movie, Screening
from marquise.domain.value_objects import CinemaId, MovieId, ScreeningId, Showtime

NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)
CONTEXT = WriteScreeningUseCase.Context(
    account="editor-1", key="write-1", reason="Correct listings"
)


@pytest.fixture
def session() -> MagicMock:
    """Inject autospecced transaction-scoped collaborators without I/O."""
    session = create_autospec(WriteScreeningUseCase.Session, instance=True)
    session.create = create_autospec(CreateScreeningUseCase, instance=True)
    session.update = create_autospec(UpdateScreeningUseCase, instance=True)
    session.delete = create_autospec(DeleteScreeningUseCase, instance=True)
    session.screenings = create_autospec(ScreeningRepository, instance=True)
    session.movies = create_autospec(MovieRepository, instance=True)
    session.find_replay.return_value = None
    saved = Screening(
        id=ScreeningId(value="scr-1"),
        movie=Movie(id=MovieId(value="mov-1"), title="Movie One"),
        cinema=Cinema(id=CinemaId(value="cin-1"), name="Cinema One"),
        showtime=Showtime(value=NOW),
        external_id="source-1",
    )
    values = dict(
        id="scr-1",
        movie_id="mov-1",
        movie_title="Movie One",
        cinema_id="cin-1",
        cinema_name="Cinema One",
        showtime=NOW,
    )
    session.screenings.find_by_id.return_value = saved
    session.movies.find_by_id.return_value = None
    session.create.execute.return_value = CreateScreeningUseCase.OutputData(**values)
    session.update.execute.return_value = UpdateScreeningUseCase.OutputData(**values)
    return session


@pytest.fixture
def transaction(session: MagicMock) -> MagicMock:
    """Provide one atomic session through the injected application interface."""
    transaction = create_autospec(ScreeningWriteTransaction, instance=True)
    transaction.open.return_value.__aenter__.return_value = session
    return transaction


@pytest.fixture
def use_case(transaction: MagicMock) -> WriteScreeningUseCase:
    """Provide deterministic time and no concrete persistence dependencies."""
    return WriteScreeningUseCase(transaction, clock=lambda: NOW)


def create_request() -> WriteScreeningUseCase.InputData:
    """A validated intended creation."""
    return WriteScreeningUseCase.InputData(
        context=CONTEXT,
        mutation=WriteScreeningUseCase.CreateInput(
            movie_id="mov-1", cinema_id="cin-1", showtime=NOW
        ),
    )


@pytest.mark.asyncio
async def test_create_records_audit_and_replay_inside_transaction(
    use_case: WriteScreeningUseCase, session: MagicMock, transaction: MagicMock
) -> None:
    """Creation records attributable persisted values and replay in one session."""
    result = await use_case.execute(create_request())
    assert result == WriteScreeningUseCase.OutputData(
        screening_id="scr-1",
        changed=True,
        screening=WriteScreeningUseCase.OutputData.Screening(
            id="scr-1",
            movie_id="mov-1",
            movie_title="Movie One",
            cinema_id="cin-1",
            cinema_name="Cinema One",
            showtime=NOW,
        ),
    )
    saved = session.save_replay.await_args.args[0].result
    assert isinstance(saved, ScreeningWriteResult)
    assert isinstance(saved.screening, ScreeningWriteResult.Screening)
    assert saved.screening.id == "scr-1"
    session.create.execute.assert_awaited_once_with(
        CreateScreeningUseCase.InputData(
            movie_id="mov-1", cinema_id="cin-1", showtime=NOW
        )
    )
    audit = session.save_audit.await_args.args[0]
    assert (audit.account, audit.key, audit.operation, audit.target) == (
        "editor-1",
        "write-1",
        "create",
        "scr-1",
    )
    assert audit.timestamp == NOW
    assert audit.reason == "Correct listings"
    assert audit.before is None
    assert audit.after.external_id == "source-1"
    session.save_replay.assert_awaited_once()
    transaction.open.return_value.__aexit__.assert_awaited_once_with(None, None, None)


@pytest.mark.asyncio
async def test_replay_uses_saved_success_without_reading_entities(
    use_case: WriteScreeningUseCase, session: MagicMock
) -> None:
    """Committed success survives later resource deletion without another audit."""
    original = await use_case.execute(create_request())
    session.find_replay.return_value = session.save_replay.await_args.args[0]
    session.create.execute.reset_mock()
    session.screenings.find_by_id.reset_mock()
    session.save_audit.reset_mock()
    session.save_replay.reset_mock()
    assert await use_case.execute(create_request()) == original
    session.create.execute.assert_not_awaited()
    session.screenings.find_by_id.assert_not_awaited()
    session.save_audit.assert_not_awaited()
    session.save_replay.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["reason", "payload", "operation"])
async def test_key_reuse_for_different_intent_fails(
    use_case: WriteScreeningUseCase, session: MagicMock, change: str
) -> None:
    """A committed key cannot represent a different reason, payload, or action."""
    request = create_request()
    await use_case.execute(request)
    session.find_replay.return_value = session.save_replay.await_args.args[0]
    if change == "reason":
        request = replace(request, context=replace(CONTEXT, reason="Another reason"))
    elif change == "payload":
        request = replace(
            request, mutation=replace(request.mutation, room="Another room")
        )
    else:
        request = replace(
            request, mutation=WriteScreeningUseCase.DeleteInput(screening_id="scr-1")
        )
    with pytest.raises(ScreeningIdempotencyConflictError):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_equivalent_timezone_replays(
    use_case: WriteScreeningUseCase, session: MagicMock
) -> None:
    """Different timezone representations of one instant have the same intent."""
    request = create_request()
    original = await use_case.execute(request)
    session.find_replay.return_value = session.save_replay.await_args.args[0]
    eastern = NOW.astimezone(timezone(timedelta(hours=-4)))
    request = replace(request, mutation=replace(request.mutation, showtime=eastern))
    assert await use_case.execute(request) == original
    session.create.execute.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("empty", [True, False])
async def test_empty_patch_and_unchanged_nonempty_patch_have_distinct_history(
    use_case: WriteScreeningUseCase, session: MagicMock, empty: bool
) -> None:
    """Empty PATCH saves replay only; explicit unchanged values still create history."""
    mutation = WriteScreeningUseCase.UpdateInput(
        screening_id="scr-1", **({} if empty else {"external_id": "source-1"})
    )
    result = await use_case.execute(
        WriteScreeningUseCase.InputData(context=CONTEXT, mutation=mutation)
    )
    assert result.changed is not empty
    session.update.execute.assert_awaited_once_with(
        UpdateScreeningUseCase.InputData(
            screening_id="scr-1",
            **({} if empty else {"external_id": "source-1"}),
        )
    )
    session.lock_target.assert_awaited_once_with("scr-1", lock_movie=False)
    session.save_replay.assert_awaited_once()
    if empty:
        session.save_audit.assert_not_awaited()
    else:
        audit = session.save_audit.await_args.args[0]
        assert audit.before == audit.after


@pytest.mark.asyncio
async def test_omission_and_explicit_null_are_different_requests(
    use_case: WriteScreeningUseCase, session: MagicMock
) -> None:
    """Reusing an empty PATCH key to clear metadata is a conflicting intent."""
    request = WriteScreeningUseCase.InputData(
        context=CONTEXT,
        mutation=WriteScreeningUseCase.UpdateInput(screening_id="scr-1"),
    )
    await use_case.execute(request)
    session.find_replay.return_value = session.save_replay.await_args.args[0]
    with pytest.raises(ScreeningIdempotencyConflictError):
        await use_case.execute(
            replace(request, mutation=replace(request.mutation, room=None))
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("orphaned", [True, False])
async def test_delete_captures_screening_and_only_removed_movie(
    use_case: WriteScreeningUseCase, session: MagicMock, orphaned: bool
) -> None:
    """Deletion records before-state and the Movie only when cleanup removes it."""
    if not orphaned:
        session.movies.find_by_id.return_value = (
            session.screenings.find_by_id.return_value.movie
        )
    result = await use_case.execute(
        WriteScreeningUseCase.InputData(
            context=CONTEXT,
            mutation=WriteScreeningUseCase.DeleteInput(screening_id="scr-1"),
        )
    )
    assert result.screening is None
    assert result.screening_id == "scr-1"
    session.delete.execute.assert_awaited_once_with(
        DeleteScreeningUseCase.InputData(screening_id="scr-1")
    )
    session.lock_target.assert_awaited_once_with("scr-1", lock_movie=True)
    audit = session.save_audit.await_args.args[0]
    assert audit.before.id == "scr-1"
    assert audit.after is None
    if orphaned:
        assert audit.removed_movie.id == "mov-1"
        assert audit.removed_movie.title == "Movie One"
    else:
        assert audit.removed_movie is None


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["save_audit", "save_replay"])
async def test_persistence_failure_exits_transaction_with_error(
    use_case: WriteScreeningUseCase,
    session: MagicMock,
    transaction: MagicMock,
    failure: str,
) -> None:
    """Audit or replay failures propagate through the atomic session for rollback."""
    getattr(session, failure).side_effect = RuntimeError("storage failure")
    with pytest.raises(RuntimeError, match="storage failure"):
        await use_case.execute(create_request())
    exit_args = transaction.open.return_value.__aexit__.await_args.args
    assert exit_args[0] is RuntimeError
    if failure == "save_audit":
        session.save_replay.assert_not_awaited()


@pytest.mark.parametrize(
    "field,value",
    [
        ("account", " "),
        ("key", ""),
        ("key", "a" * 129),
        ("key", "has space"),
        ("key", "é"),
        ("reason", " "),
        ("reason", "r" * 501),
        ("reason", "line\nfeed"),
        ("reason", "hidden\x7f"),
    ],
)
def test_context_rejects_invalid_intent(field: str, value: str) -> None:
    """Identity, key, and reason limits are enforced without reflecting secrets."""
    with pytest.raises(ValueError):
        replace(CONTEXT, **{field: value})


@pytest.mark.asyncio
async def test_naive_audit_clock_is_rejected(
    transaction: MagicMock, session: MagicMock
) -> None:
    """Invalid injected time cannot produce a misleading audit timestamp."""
    use_case = WriteScreeningUseCase(
        transaction, clock=lambda: NOW.replace(tzinfo=None)
    )
    with pytest.raises(ValueError, match="timezone"):
        await use_case.execute(create_request())
    session.save_audit.assert_not_awaited()
