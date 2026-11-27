"""Unit tests for the cinema display adapter."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.readers import CinemaReader
from marquise.interface_adapters.readers.cinema_read_gateway import CinemaReadGateway
from marquise.interface_adapters.readers.cinema_reader import PostgresCinemaReader


@pytest.mark.asyncio
async def test_find_by_id_maps_gateway_row() -> None:
    """A gateway row becomes cinema display data without an entity."""
    gateway = create_autospec(CinemaReadGateway, instance=True)
    gateway.find_by_id.return_value = {
        "id": "cin-1",
        "name": "Cinema One",
        "address": None,
        "city": "Montréal",
        "website": None,
    }

    result = await PostgresCinemaReader(gateway=gateway).find_by_id("cin-1")

    assert result == CinemaReader.CinemaData(
        id="cin-1", name="Cinema One", address=None, city="Montréal", website=None
    )
    gateway.find_by_id.assert_awaited_once_with("cin-1")


@pytest.mark.asyncio
async def test_find_by_id_returns_none_when_missing() -> None:
    """A missing gateway row means no cinema."""
    gateway = create_autospec(CinemaReadGateway, instance=True)
    gateway.find_by_id.return_value = None

    assert await PostgresCinemaReader(gateway=gateway).find_by_id("missing") is None
