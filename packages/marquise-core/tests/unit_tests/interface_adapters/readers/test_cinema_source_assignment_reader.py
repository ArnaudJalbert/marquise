"""Unit tests for PostgresCinemaSourceAssignmentReader."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from marquise.application.readers import CinemaSourceAssignmentData
from marquise.interface_adapters.readers.cinema_source_assignment_reader import (
    PostgresCinemaSourceAssignmentReader,
)


@pytest.mark.asyncio
async def test_list_all_returns_assignment_display_data() -> None:
    """Verify reader maps selected assignment fields without database I/O."""
    connection = AsyncMock()
    connection.fetch.return_value = [
        {"cinema_id": "cin-001", "source_display_name": "Cineplex"}
    ]
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=connection)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await PostgresCinemaSourceAssignmentReader(
        pool, "marquise-test"
    ).list_all()

    assert result == [CinemaSourceAssignmentData("cin-001", "Cineplex")]
    connection.fetch.assert_awaited_once()
