"""Unit tests for PostgresCinemaSourceAssignmentReader."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.readers import CinemaSourceAssignmentReader
from marquise.interface_adapters.gateways.cinema_source_assignment_reader import (
    CinemaSourceAssignmentReadGateway,
)
from marquise.interface_adapters.readers.cinema_source_assignment_reader import (
    PostgresCinemaSourceAssignmentReader,
)

ROW = {
    "cinema_id": "cin-001",
    "source_name": "cineplex",
    "source_display_name": "Cineplex",
}
DATA = CinemaSourceAssignmentReader.CinemaSourceAssignmentData(
    cinema_id="cin-001", source_name="cineplex", source_display_name="Cineplex"
)


@pytest.fixture
def gateway() -> CinemaSourceAssignmentReadGateway:
    """Provide a gateway mock that matches the read gateway protocol."""
    return create_autospec(CinemaSourceAssignmentReadGateway, instance=True)


@pytest.fixture
def reader(
    gateway: CinemaSourceAssignmentReadGateway,
) -> PostgresCinemaSourceAssignmentReader:
    """Provide the reader over the mocked gateway."""
    return PostgresCinemaSourceAssignmentReader(gateway)


@pytest.mark.asyncio
async def test_list_all_maps_gateway_rows(
    reader: PostgresCinemaSourceAssignmentReader,
    gateway: CinemaSourceAssignmentReadGateway,
) -> None:
    """Every gateway row becomes one assignment read model."""
    gateway.list_all.return_value = [ROW]

    assert await reader.list_all() == [DATA]


@pytest.mark.asyncio
async def test_find_by_cinema_id_maps_gateway_row(
    reader: PostgresCinemaSourceAssignmentReader,
    gateway: CinemaSourceAssignmentReadGateway,
) -> None:
    """An assigned cinema's row becomes its assignment read model."""
    gateway.find_by_cinema_id.return_value = ROW

    assert await reader.find_by_cinema_id("cin-001") == DATA
    gateway.find_by_cinema_id.assert_awaited_once_with("cin-001")


@pytest.mark.asyncio
async def test_find_by_cinema_id_returns_none_when_unassigned(
    reader: PostgresCinemaSourceAssignmentReader,
    gateway: CinemaSourceAssignmentReadGateway,
) -> None:
    """A cinema with no assignment row reads as None."""
    gateway.find_by_cinema_id.return_value = None

    assert await reader.find_by_cinema_id("cin-001") is None
