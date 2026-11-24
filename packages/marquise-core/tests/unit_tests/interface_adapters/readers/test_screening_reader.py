"""Unit tests for the pure screening display adapter."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import create_autospec

import pytest

from marquise.application.readers import ScreeningReader
from marquise.interface_adapters.readers.screening_read_gateway import (
    ScreeningReadGateway,
)
from marquise.interface_adapters.readers.screening_reader import (
    PostgresScreeningReader,
)
from marquise.interface_adapters.repositories.protocols.base import (
    GatewayError,
    GatewayPage,
)


def _row() -> dict:
    return {
        "id": "scr-1",
        "movie_id": "mov-1",
        "movie_title": "The Odyssey",
        "cinema_id": "cin-1",
        "cinema_name": "Cinema One",
        "showtime": datetime(2026, 6, 27, 19, 30),
        "ticket_url": None,
        "room": None,
        "language": "V.O.",
    }


@pytest.mark.asyncio
async def test_find_by_id_maps_single_exact_projection_lookup() -> None:
    """An injected gateway supplies one display row without entity hydration."""
    gateway = create_autospec(ScreeningReadGateway, instance=True)
    gateway.find_by_id.return_value = {
        **_row(),
        "ticket_url": "https://cinema.example/tickets/scr-1",
        "room": "Room 2",
    }

    result = await PostgresScreeningReader(gateway=gateway).find_by_id("scr-1")

    assert result == ScreeningReader.ScreeningData(
        id="scr-1",
        movie_id="mov-1",
        movie_title="The Odyssey",
        cinema_id="cin-1",
        cinema_name="Cinema One",
        showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
        ticket_url="https://cinema.example/tickets/scr-1",
        room="Room 2",
        language="V.O.",
    )
    gateway.find_by_id.assert_awaited_once_with("scr-1")
    gateway.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_find_by_id_returns_none_when_missing() -> None:
    """A missing projection returns None without a fallback search."""
    gateway = create_autospec(ScreeningReadGateway, instance=True)
    gateway.find_by_id.return_value = None

    result = await PostgresScreeningReader(gateway).find_by_id("missing")

    assert result is None
    gateway.find_by_id.assert_awaited_once_with("missing")
    gateway.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_find_by_id_defaults_absent_optional_fields() -> None:
    """Only display identifiers, labels and showtime are needed to map a row."""
    gateway = create_autospec(ScreeningReadGateway, instance=True)
    row = _row()
    for field in ("ticket_url", "room", "language"):
        row.pop(field)
    gateway.find_by_id.return_value = row

    result = await PostgresScreeningReader(gateway).find_by_id("scr-1")

    assert result is not None
    assert result.ticket_url is None
    assert result.room is None
    assert result.language is None


@pytest.mark.asyncio
async def test_find_by_id_preserves_aware_showtime() -> None:
    """An already aware UTC timestamp is not stripped or shifted."""
    gateway = create_autospec(ScreeningReadGateway, instance=True)
    showtime = datetime(2026, 6, 27, 19, 30, tzinfo=UTC)
    gateway.find_by_id.return_value = {**_row(), "showtime": showtime}

    result = await PostgresScreeningReader(gateway).find_by_id("scr-1")

    assert result is not None
    assert result.showtime is showtime


@pytest.mark.asyncio
async def test_search_maps_projection_and_delegates_filters_unchanged() -> None:
    """Mapping leaves filtering and input timezone conversion to the gateway."""
    gateway = create_autospec(ScreeningReadGateway, instance=True)
    row = _row()
    gateway.search.return_value = GatewayPage(rows=[row], total=12)
    reader = PostgresScreeningReader(gateway)
    eastern = timezone(timedelta(hours=-4))
    start = datetime(2026, 6, 27, tzinfo=eastern)
    end = datetime(2026, 6, 28, tzinfo=eastern)

    result = await reader.search(
        movie_id="mov-1",
        movie_title="Odyssey",
        cinema_id="cin-1",
        start_date=start,
        end_date=end,
        language="V.O.",
        limit=5,
        offset=10,
    )

    assert result.items == [
        ScreeningReader.ScreeningData(
            id="scr-1",
            movie_id="mov-1",
            movie_title="The Odyssey",
            cinema_id="cin-1",
            cinema_name="Cinema One",
            showtime=datetime(2026, 6, 27, 19, 30, tzinfo=UTC),
            language="V.O.",
        )
    ]
    assert result.total == 12
    gateway.search.assert_awaited_once_with(
        movie_id="mov-1",
        movie_title="Odyssey",
        cinema_id="cin-1",
        start_date=start,
        end_date=end,
        language="V.O.",
        limit=5,
        offset=10,
    )
    gateway.find_by_id.assert_not_awaited()
    assert row["showtime"].tzinfo is None


@pytest.mark.asyncio
async def test_search_preserves_gateway_row_order() -> None:
    """Projection mapping preserves the gateway's stable pagination order."""
    gateway = create_autospec(ScreeningReadGateway, instance=True)
    gateway.search.return_value = GatewayPage(
        rows=[{**_row(), "id": "scr-2"}, _row()], total=2
    )

    result = await PostgresScreeningReader(gateway).search(limit=5)

    assert [item.id for item in result.items] == ["scr-2", "scr-1"]
    assert result.total == 2


@pytest.mark.asyncio
async def test_search_without_filters_delegates_defaults() -> None:
    """Unbounded search forwards the complete default contract to its gateway."""
    gateway = create_autospec(ScreeningReadGateway, instance=True)
    gateway.search.return_value = GatewayPage(rows=[_row()], total=1)

    result = await PostgresScreeningReader(gateway).search()

    assert len(result.items) == 1
    assert result.total == 1
    gateway.search.assert_awaited_once_with(
        movie_id=None,
        movie_title=None,
        cinema_id=None,
        start_date=None,
        end_date=None,
        language=None,
        limit=None,
        offset=0,
    )


@pytest.mark.asyncio
async def test_search_empty_page_preserves_gateway_total() -> None:
    """A page beyond the results retains the true total supplied by the gateway."""
    gateway = create_autospec(ScreeningReadGateway, instance=True)
    gateway.search.return_value = GatewayPage(rows=[], total=3)

    result = await PostgresScreeningReader(gateway).search(
        movie_title="Odyssey", limit=5, offset=10
    )

    assert result.items == []
    assert result.total == 3
    gateway.search.assert_awaited_once_with(
        movie_id=None,
        movie_title="Odyssey",
        cinema_id=None,
        start_date=None,
        end_date=None,
        language=None,
        limit=5,
        offset=10,
    )


@pytest.mark.asyncio
async def test_find_by_id_propagates_gateway_failure() -> None:
    """A data-layer failure is not disguised as a missing projection."""
    gateway = create_autospec(ScreeningReadGateway, instance=True)
    gateway.find_by_id.side_effect = GatewayError("projection unavailable")

    with pytest.raises(GatewayError, match="projection unavailable"):
        await PostgresScreeningReader(gateway).find_by_id("scr-1")

    gateway.find_by_id.assert_awaited_once_with("scr-1")
    gateway.search.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_propagates_gateway_failure() -> None:
    """A search failure is not disguised as an empty result page."""
    gateway = create_autospec(ScreeningReadGateway, instance=True)
    gateway.search.side_effect = GatewayError("projection unavailable")

    with pytest.raises(GatewayError, match="projection unavailable"):
        await PostgresScreeningReader(gateway).search()

    gateway.search.assert_awaited_once()
    gateway.find_by_id.assert_not_awaited()
