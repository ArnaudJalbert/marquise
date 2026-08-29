"""Unit tests for SupabaseScreeningGateway query behavior."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from marquise.infrastructure.supabase.gateways.screening import (
    SupabaseScreeningGateway,
)


class _Connection:
    async def fetch(self, query: str, *params: object) -> list[dict]:
        """Return one row after checking the pagination ordering."""
        assert "ORDER BY s.showtime, s.id" in query
        return [{"id": "scr-a-first", "__total": 1}]


class _Acquire:
    async def __aenter__(self) -> _Connection:
        return _Connection()

    async def __aexit__(self, *args: object) -> None:
        return None


class _Pool:
    def acquire(self) -> _Acquire:
        return _Acquire()


@pytest.mark.asyncio
async def test_search_uses_deterministic_order_for_offset_pagination() -> None:
    """Equal showtimes use screening ID as a stable pagination tie-breaker."""
    gateway = SupabaseScreeningGateway(pool=_Pool())

    page = await gateway.search(
        start_date=datetime(2026, 6, 7, tzinfo=UTC),
        end_date=datetime(2026, 6, 8, tzinfo=UTC),
        limit=1,
        offset=0,
    )

    assert page.total == 1
    assert page.rows[0]["id"] == "scr-a-first"
