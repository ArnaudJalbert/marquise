"""Tests for SourceController."""

from __future__ import annotations

from unittest.mock import AsyncMock, create_autospec

import pytest

from marquise.application.use_cases.assign_source import AssignSourceUseCase
from marquise.application.use_cases.create_source import CreateSourceUseCase
from marquise.application.use_cases.delete_source import DeleteSourceUseCase
from marquise.application.use_cases.get_cinema_source import GetCinemaSourceUseCase
from marquise.application.use_cases.import_screenings import (
    ImportScreeningsUseCase,
)
from marquise.application.use_cases.list_registry_sources import (
    ListRegistrySourcesUseCase,
)
from marquise.application.use_cases.list_sources import ListSourcesUseCase
from marquise.application.use_cases.unassign_source import UnassignSourceUseCase
from marquise.infrastructure.controllers.auth_controller import AuthController
from marquise.infrastructure.controllers.source_controller import SourceController
from marquise.interface_adapters.repositories.protocols.auth import AuthSession


@pytest.fixture
def mock_auth_controller() -> AuthController:
    """Provide a mocked AuthController."""
    return create_autospec(AuthController, instance=True)


@pytest.fixture
def mock_create_use_case() -> CreateSourceUseCase:
    """Provide a mocked CreateSourceUseCase."""
    return create_autospec(CreateSourceUseCase, instance=True)


@pytest.fixture
def mock_list_use_case() -> ListSourcesUseCase:
    """Provide a mocked ListSourcesUseCase."""
    return create_autospec(ListSourcesUseCase, instance=True)


@pytest.fixture
def mock_delete_use_case() -> DeleteSourceUseCase:
    """Provide a mocked DeleteSourceUseCase."""
    return create_autospec(DeleteSourceUseCase, instance=True)


@pytest.fixture
def mock_assign_use_case() -> AssignSourceUseCase:
    """Provide a mocked AssignSourceUseCase."""
    return create_autospec(AssignSourceUseCase, instance=True)


@pytest.fixture
def mock_unassign_use_case() -> UnassignSourceUseCase:
    """Provide a mocked UnassignSourceUseCase."""
    return create_autospec(UnassignSourceUseCase, instance=True)


@pytest.fixture
def mock_get_use_case() -> GetCinemaSourceUseCase:
    """Provide a mocked GetCinemaSourceUseCase."""
    return create_autospec(GetCinemaSourceUseCase, instance=True)


@pytest.fixture
def mock_list_registry_use_case() -> ListRegistrySourcesUseCase:
    """Provide a mocked ListRegistrySourcesUseCase."""
    return create_autospec(ListRegistrySourcesUseCase, instance=True)


@pytest.fixture
def mock_import_use_case() -> ImportScreeningsUseCase:
    """Provide a mocked ImportScreeningsUseCase."""
    return create_autospec(ImportScreeningsUseCase, instance=True)


@pytest.fixture
def controller(
    mock_auth_controller: AuthController,
    mock_create_use_case: CreateSourceUseCase,
    mock_list_use_case: ListSourcesUseCase,
    mock_delete_use_case: DeleteSourceUseCase,
    mock_assign_use_case: AssignSourceUseCase,
    mock_unassign_use_case: UnassignSourceUseCase,
    mock_get_use_case: GetCinemaSourceUseCase,
    mock_list_registry_use_case: ListRegistrySourcesUseCase,
    mock_import_use_case: ImportScreeningsUseCase,
) -> SourceController:
    """Provide a SourceController wired to mocks."""
    return SourceController(
        auth_controller=mock_auth_controller,
        create_source_use_case=mock_create_use_case,
        list_sources_use_case=mock_list_use_case,
        delete_source_use_case=mock_delete_use_case,
        assign_source_use_case=mock_assign_use_case,
        unassign_source_use_case=mock_unassign_use_case,
        get_cinema_source_use_case=mock_get_use_case,
        list_registry_sources_use_case=mock_list_registry_use_case,
        import_screenings_use_case=mock_import_use_case,
    )


# ── create_source ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_source_validates_admin_then_delegates(
    controller: SourceController,
    mock_auth_controller: AuthController,
    mock_create_use_case: CreateSourceUseCase,
) -> None:
    """Verify create_source validates admin, then delegates to the use case."""
    mock_auth_controller.validate_admin.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    expected = CreateSourceUseCase.OutputData(
        name="cineplex",
        display_name="Cineplex",
        description="Cineplex cinemas",
    )
    mock_create_use_case.execute = AsyncMock(return_value=expected)

    result = await controller.create_source(
        name="cineplex",
        display_name="Cineplex",
        description="Cineplex cinemas",
    )

    assert result == expected
    mock_auth_controller.validate_admin.assert_called_once_with()
    mock_create_use_case.execute.assert_awaited_once()
    input_data = mock_create_use_case.execute.call_args[0][0]
    assert isinstance(input_data, CreateSourceUseCase.InputData)
    assert input_data.name == "cineplex"


@pytest.mark.asyncio
async def test_create_source_raises_when_not_admin(
    controller: SourceController,
    mock_auth_controller: AuthController,
    mock_create_use_case: CreateSourceUseCase,
) -> None:
    """Verify create_source propagates ValueError when admin validation fails."""
    mock_auth_controller.validate_admin.side_effect = ValueError("Access denied")

    with pytest.raises(ValueError, match="Access denied"):
        await controller.create_source(name="s", display_name="S")

    mock_create_use_case.execute.assert_not_called()


# ── list_sources ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sources_validates_admin_then_delegates(
    controller: SourceController,
    mock_auth_controller: AuthController,
    mock_list_use_case: ListSourcesUseCase,
) -> None:
    """Verify list_sources validates admin, then delegates."""
    mock_auth_controller.validate_admin.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    source_data = ListSourcesUseCase.SourceData(name="s", display_name="S")
    expected = ListSourcesUseCase.OutputData(sources=[source_data])
    mock_list_use_case.execute = AsyncMock(return_value=expected)

    result = await controller.list_sources()

    assert result == expected
    mock_auth_controller.validate_admin.assert_called_once_with()
    mock_list_use_case.execute.assert_awaited_once()


# ── delete_source ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_source_validates_admin_then_delegates(
    controller: SourceController,
    mock_auth_controller: AuthController,
    mock_delete_use_case: DeleteSourceUseCase,
) -> None:
    """Verify delete_source validates admin, then delegates."""
    mock_auth_controller.validate_admin.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    expected = DeleteSourceUseCase.OutputData(source_name="cineplex")
    mock_delete_use_case.execute = AsyncMock(return_value=expected)

    result = await controller.delete_source(source_name="cineplex")

    assert result == expected
    mock_auth_controller.validate_admin.assert_called_once_with()
    mock_delete_use_case.execute.assert_awaited_once()
    input_data = mock_delete_use_case.execute.call_args[0][0]
    assert isinstance(input_data, DeleteSourceUseCase.InputData)
    assert input_data.source_name == "cineplex"


# ── assign_source ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assign_source_validates_admin_then_delegates(
    controller: SourceController,
    mock_auth_controller: AuthController,
    mock_assign_use_case: AssignSourceUseCase,
) -> None:
    """Verify assign_source validates admin, then delegates."""
    mock_auth_controller.validate_admin.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    expected = AssignSourceUseCase.OutputData(
        cinema_id="cin-001", source_name="cineplex"
    )
    mock_assign_use_case.execute = AsyncMock(return_value=expected)

    result = await controller.assign_source(cinema_id="cin-001", source_name="cineplex")

    assert result == expected
    mock_auth_controller.validate_admin.assert_called_once_with()
    mock_assign_use_case.execute.assert_awaited_once()
    input_data = mock_assign_use_case.execute.call_args[0][0]
    assert isinstance(input_data, AssignSourceUseCase.InputData)
    assert input_data.cinema_id == "cin-001"
    assert input_data.source_name == "cineplex"


# ── unassign_source ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unassign_source_validates_admin_then_delegates(
    controller: SourceController,
    mock_auth_controller: AuthController,
    mock_unassign_use_case: UnassignSourceUseCase,
) -> None:
    """Verify unassign_source validates admin, then delegates."""
    mock_auth_controller.validate_admin.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    expected = UnassignSourceUseCase.OutputData(cinema_id="cin-001")
    mock_unassign_use_case.execute = AsyncMock(return_value=expected)

    result = await controller.unassign_source(cinema_id="cin-001")

    assert result == expected
    mock_auth_controller.validate_admin.assert_called_once_with()
    mock_unassign_use_case.execute.assert_awaited_once()
    input_data = mock_unassign_use_case.execute.call_args[0][0]
    assert isinstance(input_data, UnassignSourceUseCase.InputData)
    assert input_data.cinema_id == "cin-001"


# ── get_cinema_source (public — no auth check) ───────────────────────────────


@pytest.mark.asyncio
async def test_get_cinema_source_delegates_without_auth_check(
    controller: SourceController,
    mock_auth_controller: AuthController,
    mock_get_use_case: GetCinemaSourceUseCase,
) -> None:
    """Verify get_cinema_source delegates without admin check (public)."""
    expected = GetCinemaSourceUseCase.OutputData(
        cinema_id="cin-001",
        source_name="cineplex",
        source_display_name="Cineplex",
    )
    mock_get_use_case.execute = AsyncMock(return_value=expected)

    result = await controller.get_cinema_source(cinema_id="cin-001")

    assert result == expected
    mock_auth_controller.validate_admin.assert_not_called()
    mock_get_use_case.execute.assert_awaited_once()
    input_data = mock_get_use_case.execute.call_args[0][0]
    assert isinstance(input_data, GetCinemaSourceUseCase.InputData)
    assert input_data.cinema_id == "cin-001"


# ── list_registry_sources (public — no auth check) ──────────────────────────


@pytest.mark.asyncio
async def test_list_registry_sources_delegates_without_auth_check(
    controller: SourceController,
    mock_auth_controller: AuthController,
    mock_list_registry_use_case: ListRegistrySourcesUseCase,
) -> None:
    """Verify list_registry_sources delegates without admin check (public)."""
    source_entry = ListRegistrySourcesUseCase.SourceEntry(
        name="cinemacinema",
    )
    expected = ListRegistrySourcesUseCase.OutputData(sources=[source_entry])
    mock_list_registry_use_case.execute = AsyncMock(return_value=expected)

    result = await controller.list_registry_sources()

    assert result == expected
    mock_auth_controller.validate_admin.assert_not_called()
    mock_list_registry_use_case.execute.assert_awaited_once()
    input_data = mock_list_registry_use_case.execute.call_args[0][0]
    assert isinstance(input_data, ListRegistrySourcesUseCase.InputData)
