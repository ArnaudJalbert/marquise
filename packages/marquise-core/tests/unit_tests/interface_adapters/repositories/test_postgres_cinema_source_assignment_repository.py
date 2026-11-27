"""Unit tests for PostgresCinemaSourceAssignmentRepository with mocked gateway."""

from __future__ import annotations

from unittest.mock import AsyncMock, create_autospec

import pytest

from marquise.application.exceptions import CinemaSourceAssignmentAlreadyExistsError
from marquise.domain.entities import Cinema, CinemaSourceAssignment, SourceDefinition
from marquise.domain.value_objects import CinemaId, SourceName
from marquise.interface_adapters.gateways.base import GatewayError
from marquise.interface_adapters.gateways.cinema_source_assignment import (
    CinemaSourceAssignmentGateway,
)
from marquise.interface_adapters.repositories.cinema_source_assignment_repository import (  # noqa: E501
    PostgresCinemaSourceAssignmentRepository,
)


@pytest.fixture
def mock_gateway() -> AsyncMock:
    """Provide a mocked CinemaSourceAssignmentGateway."""
    return create_autospec(CinemaSourceAssignmentGateway, instance=True)


@pytest.fixture
def repo(
    mock_gateway: AsyncMock,
) -> PostgresCinemaSourceAssignmentRepository:
    """Provide a repository wired to the mock gateway."""
    return PostgresCinemaSourceAssignmentRepository(gateway=mock_gateway)


@pytest.fixture
def sample_cinema() -> Cinema:
    """Provide a sample Cinema for tests."""
    return Cinema(id=CinemaId(value="cin-001"), name="Test Cinema")


@pytest.fixture
def sample_source() -> SourceDefinition:
    """Provide a sample SourceDefinition for tests."""
    return SourceDefinition(name=SourceName(value="cineplex"), display_name="Cineplex")


def _gateway_row() -> dict:
    return {
        "cinema_id": "cin-001",
        "source_name": "cineplex",
        "cinema__id": "cin-001",
        "cinema__name": "Test Cinema",
        "cinema__address": None,
        "cinema__city": None,
        "cinema__website": None,
        "source__name": "cineplex",
        "source__display_name": "Cineplex",
        "source__description": None,
    }


@pytest.mark.asyncio
async def test_assign(
    repo: PostgresCinemaSourceAssignmentRepository,
    mock_gateway: AsyncMock,
    sample_cinema: Cinema,
    sample_source: SourceDefinition,
) -> None:
    """Verify assign delegates to the gateway and maps the result."""
    mock_gateway.assign.return_value = {
        "cinema_id": "cin-001",
        "source_name": "cineplex",
    }

    assignment = CinemaSourceAssignment(cinema=sample_cinema, source=sample_source)
    result = await repo.assign(assignment)

    assert result.cinema == sample_cinema
    assert result.source == sample_source
    mock_gateway.assign.assert_awaited_once_with(
        cinema_id="cin-001", source_name="cineplex"
    )


@pytest.mark.asyncio
async def test_assign_raises_on_gateway_error(
    repo: PostgresCinemaSourceAssignmentRepository,
    mock_gateway: AsyncMock,
    sample_cinema: Cinema,
    sample_source: SourceDefinition,
) -> None:
    """Verify assign wraps GatewayError as CinemaSourceAssignmentAlreadyExistsError."""
    mock_gateway.assign.side_effect = GatewayError("already assigned")

    assignment = CinemaSourceAssignment(cinema=sample_cinema, source=sample_source)
    with pytest.raises(
        CinemaSourceAssignmentAlreadyExistsError, match="already assigned"
    ):
        await repo.assign(assignment)


@pytest.mark.asyncio
async def test_unassign(
    repo: PostgresCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify unassign delegates to the gateway and returns True."""
    mock_gateway.unassign.return_value = True

    result = await repo.unassign(CinemaId(value="cin-001"))
    assert result is True
    mock_gateway.unassign.assert_awaited_once_with("cin-001")


@pytest.mark.asyncio
async def test_unassign_missing(
    repo: PostgresCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify unassign returns False when no assignment exists."""
    mock_gateway.unassign.return_value = False

    result = await repo.unassign(CinemaId(value="missing"))
    assert result is False


@pytest.mark.asyncio
async def test_find_by_cinema_id(
    repo: PostgresCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_cinema_id delegates and maps the result."""
    mock_gateway.find_by_cinema_id.return_value = _gateway_row()

    result = await repo.find_by_cinema_id(CinemaId(value="cin-001"))
    assert result is not None
    assert result.cinema.id == CinemaId(value="cin-001")
    assert result.source.name == SourceName(value="cineplex")
    mock_gateway.find_by_cinema_id.assert_awaited_once_with("cin-001")


@pytest.mark.asyncio
async def test_find_by_cinema_id_missing(
    repo: PostgresCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_cinema_id returns None when not found."""
    mock_gateway.find_by_cinema_id.return_value = None

    result = await repo.find_by_cinema_id(CinemaId(value="missing"))
    assert result is None
