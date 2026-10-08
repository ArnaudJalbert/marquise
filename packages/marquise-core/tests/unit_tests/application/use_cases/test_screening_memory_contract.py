"""The in-memory adapter obeys the same checked persistence contract."""

from collections.abc import Awaitable, Callable

import pytest

from marquise.application.repositories import ScreeningRepository
from marquise.domain.entities import Screening
from support.screening_contract import (
    assert_checked_writes,
    assert_removed_owner,
    assert_target_arrival,
)
from support.screening_import import owner
from support.screening_memory import MemoryScreeningRepository


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario", [assert_checked_writes, assert_target_arrival, assert_removed_owner]
)
async def test_memory_checked_write_contract(
    scenario: Callable[[ScreeningRepository, Screening], Awaitable[None]],
) -> None:
    """An in-memory adapter checks stale rows and arrivals atomically."""
    await scenario(MemoryScreeningRepository(), owner())
