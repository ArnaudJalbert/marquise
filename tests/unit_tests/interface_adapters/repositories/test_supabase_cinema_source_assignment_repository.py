"""Unit tests for SupabaseCinemaSourceAssignmentRepository with mocked gateway."""

from __future__ import annotations

from unittest.mock import AsyncMock, create_autospec

import pytest

from marquise.application.exceptions import CinemaSourceAssignmentAlreadyExistsError
from marquise.domain.entities import CinemaSourceAssignment
from marquise.domain.value_objects import CinemaId, SourceName
from marquise.interface_adapters.repositories.protocols.cinema import GatewayError
from marquise.interface_adapters.repositories.protocols.cinema_source_assignment import (  # noqa: E501
    CinemaSourceAssignmentGateway,
)
from marquise.interface_adapters.repositories.supabase.cinema_source_assignment_repository import (  # noqa: E501
    SupabaseCinemaSourceAssignmentRepository,
)


@pytest.fixture
def mock_gateway() -> AsyncMock:
    """Provide a mocked CinemaSourceAssignmentGateway."""
    return create_autospec(CinemaSourceAssignmentGateway, instance=True)


@pytest.fixture
def repo(
    mock_gateway: AsyncMock,
) -> SupabaseCinemaSourceAssignmentRepository:
    """Provide a repository wired to the mock gateway."""
    return SupabaseCinemaSourceAssignmentRepository(gateway=mock_gateway)


def _gateway_row(cinema_id: str = "cin-001", source_name: str = "cineplex") -> dict:
    return {"cinema_id": cinema_id, "source_name": source_name}


@pytest.mark.asyncio
async def test_assign(
    repo: SupabaseCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify assign delegates to the gateway and maps the result."""
    mock_gateway.assign.return_value = _gateway_row()

    assignment = CinemaSourceAssignment(
        cinema_id=CinemaId(value="cin-001"),
        source_name=SourceName(value="cineplex"),
    )
    result = await repo.assign(assignment)

    assert result.cinema_id == CinemaId(value="cin-001")
    assert result.source_name == SourceName(value="cineplex")
    mock_gateway.assign.assert_awaited_once_with(
        cinema_id="cin-001", source_name="cineplex"
    )


@pytest.mark.asyncio
async def test_assign_raises_on_gateway_error(
    repo: SupabaseCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify assign wraps GatewayError as CinemaSourceAssignmentAlreadyExistsError."""
    mock_gateway.assign.side_effect = GatewayError("already assigned")

    assignment = CinemaSourceAssignment(
        cinema_id=CinemaId(value="cin-001"),
        source_name=SourceName(value="cineplex"),
    )
    with pytest.raises(
        CinemaSourceAssignmentAlreadyExistsError, match="already assigned"
    ):
        await repo.assign(assignment)


@pytest.mark.asyncio
async def test_unassign(
    repo: SupabaseCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify unassign delegates to the gateway and returns True."""
    mock_gateway.unassign.return_value = True

    result = await repo.unassign(CinemaId(value="cin-001"))
    assert result is True
    mock_gateway.unassign.assert_awaited_once_with("cin-001")


@pytest.mark.asyncio
async def test_unassign_missing(
    repo: SupabaseCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify unassign returns False when no assignment exists."""
    mock_gateway.unassign.return_value = False

    result = await repo.unassign(CinemaId(value="missing"))
    assert result is False


@pytest.mark.asyncio
async def test_find_by_cinema_id(
    repo: SupabaseCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_cinema_id delegates and maps the result."""
    mock_gateway.find_by_cinema_id.return_value = _gateway_row()

    result = await repo.find_by_cinema_id(CinemaId(value="cin-001"))
    assert result is not None
    assert result.cinema_id == CinemaId(value="cin-001")
    assert result.source_name == SourceName(value="cineplex")
    mock_gateway.find_by_cinema_id.assert_awaited_once_with("cin-001")


@pytest.mark.asyncio
async def test_find_by_cinema_id_missing(
    repo: SupabaseCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_by_cinema_id returns None when not found."""
    mock_gateway.find_by_cinema_id.return_value = None

    result = await repo.find_by_cinema_id(CinemaId(value="missing"))
    assert result is None


@pytest.mark.asyncio
async def test_find_all(
    repo: SupabaseCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_all returns all mapped assignments."""
    mock_gateway.find_all.return_value = [
        _gateway_row("cin-001", "cineplex"),
        _gateway_row("cin-002", "cinema_du_parc"),
    ]

    result = await repo.find_all()
    assert len(result) == 2
    assert result[0].cinema_id == CinemaId(value="cin-001")
    assert result[1].source_name == SourceName(value="cinema_du_parc")
    mock_gateway.find_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_all_empty(
    repo: SupabaseCinemaSourceAssignmentRepository, mock_gateway: AsyncMock
) -> None:
    """Verify find_all returns empty list when no assignments exist."""
    mock_gateway.find_all.return_value = []

    result = await repo.find_all()
    assert result == []
