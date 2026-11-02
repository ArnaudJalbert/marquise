"""Audit/replay mappings through the injected plain-data gateway interface."""

from dataclasses import asdict
from datetime import UTC, datetime
from unittest.mock import MagicMock, create_autospec

import pytest

from marquise.application.repositories import MovieRepository, ScreeningRepository
from marquise.application.transactions.screening_write import (
    ScreeningReplay,
    ScreeningWriteResult,
)
from marquise.application.use_cases.create_screening import CreateScreeningUseCase
from marquise.application.use_cases.delete_screening import DeleteScreeningUseCase
from marquise.application.use_cases.update_screening import UpdateScreeningUseCase
from marquise.domain.value_objects.screening_audit import ScreeningAuditRecord
from marquise.interface_adapters.repositories.protocols.screening_write import (
    ScreeningWriteGateway,
)
from marquise.interface_adapters.repositories.screening_write import (
    ScreeningWriteSessionAdapter,
)

NOW = datetime(2026, 10, 7, 12, tzinfo=UTC)


@pytest.fixture
def gateway() -> MagicMock:
    """Use an autospecced gateway without database or network access."""
    return create_autospec(ScreeningWriteGateway, instance=True)


@pytest.fixture
def adapter(gateway: MagicMock) -> ScreeningWriteSessionAdapter:
    """Inject all collaborators; the adapter never constructs storage or use cases."""
    return ScreeningWriteSessionAdapter(
        gateway,
        create=create_autospec(CreateScreeningUseCase, instance=True),
        update=create_autospec(UpdateScreeningUseCase, instance=True),
        delete=create_autospec(DeleteScreeningUseCase, instance=True),
        screenings=create_autospec(ScreeningRepository, instance=True),
        movies=create_autospec(MovieRepository, instance=True),
    )


@pytest.mark.asyncio
async def test_absent_replay_maps_to_none(
    adapter: ScreeningWriteSessionAdapter, gateway: MagicMock
) -> None:
    """A new account/key has no committed result."""
    gateway.find_replay.return_value = None
    assert await adapter.find_replay() is None


@pytest.mark.asyncio
@pytest.mark.parametrize("deleted", [False, True])
async def test_replay_maps_durable_result_without_live_entities(
    adapter: ScreeningWriteSessionAdapter, gateway: MagicMock, deleted: bool
) -> None:
    """Stored creation and deletion results reconstruct typed application output."""
    screening = (
        None
        if deleted
        else ScreeningWriteResult.Screening(
            id="scr-1",
            movie_id="mov-1",
            movie_title="Movie One",
            cinema_id="cin-1",
            cinema_name="Cinema One",
            showtime=NOW,
        )
    )
    result = ScreeningWriteResult(
        screening_id="scr-1", changed=True, screening=screening
    )
    data = asdict(result)
    if not deleted:
        data["screening"]["showtime"] = "2026-10-07T12:00:00+00:00"
    gateway.find_replay.return_value = {"fingerprint": "fingerprint-1", "result": data}
    assert await adapter.find_replay() == ScreeningReplay(
        fingerprint="fingerprint-1", result=result
    )
    adapter.screenings.find_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_history_mapping_only_contains_selected_fields(
    adapter: ScreeningWriteSessionAdapter, gateway: MagicMock
) -> None:
    """Application history maps to explicit fields, never request or token data."""
    record = ScreeningAuditRecord(
        account="editor-1",
        key="delete-1",
        operation="delete",
        target="scr-1",
        timestamp=NOW,
        reason="Remove obsolete listing",
        before=None,
        after=None,
    )
    await adapter.save_audit(record)
    data = gateway.save_audit.await_args.args[0]
    assert set(data) == {
        "account",
        "key",
        "operation",
        "target",
        "timestamp",
        "reason",
        "before",
        "after",
        "removed_movie",
    }
    assert data["account"] == "editor-1"
    assert data["timestamp"] == NOW


@pytest.mark.asyncio
async def test_replay_mapping_and_lock_delegation(
    adapter: ScreeningWriteSessionAdapter, gateway: MagicMock
) -> None:
    """Persistence receives plain success data and the required target lock intent."""
    replay = ScreeningReplay(
        fingerprint="fingerprint-1",
        result=ScreeningWriteResult(screening_id="scr-1", changed=True),
    )
    await adapter.save_replay(replay)
    gateway.save_replay.assert_awaited_once_with(
        {
            "fingerprint": "fingerprint-1",
            "result": {"screening_id": "scr-1", "changed": True, "screening": None},
        }
    )
    await adapter.lock_target("scr-1", lock_movie=True)
    gateway.lock_target.assert_awaited_once_with("scr-1", lock_movie=True)
