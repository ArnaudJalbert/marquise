"""Tests for CinemaController."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.use_cases.create_cinema import CreateCinemaUseCase
from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.get_cinema import GetCinemaUseCase
from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_screenings import (
    GetCinemaScreeningsUseCase,
)
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase
from marquise.infrastructure.controllers.auth_controller import AuthController
from marquise.infrastructure.controllers.cinema_controller import CinemaController
from marquise.interface_adapters.repositories.protocols.auth import AuthSession


@pytest.fixture
def mock_auth_controller() -> AuthController:
    """Provide a mocked AuthController."""
    return create_autospec(AuthController, instance=True)


@pytest.fixture
def mock_create_use_case() -> CreateCinemaUseCase:
    """Provide a mocked CreateCinemaUseCase."""
    return create_autospec(CreateCinemaUseCase, instance=True)


@pytest.fixture
def mock_delete_use_case() -> DeleteCinemaUseCase:
    """Provide a mocked DeleteCinemaUseCase."""
    return create_autospec(DeleteCinemaUseCase, instance=True)


@pytest.fixture
def mock_list_use_case() -> ListCinemasUseCase:
    """Provide a mocked ListCinemasUseCase."""
    return create_autospec(ListCinemasUseCase, instance=True)


@pytest.fixture
def mock_update_use_case() -> UpdateCinemaUseCase:
    """Provide a mocked UpdateCinemaUseCase."""
    return create_autospec(UpdateCinemaUseCase, instance=True)


@pytest.fixture
def mock_get_use_case() -> GetCinemaUseCase:
    """Provide a mocked GetCinemaUseCase."""
    return create_autospec(GetCinemaUseCase, instance=True)


@pytest.fixture
def mock_get_movies_use_case() -> GetCinemaMoviesUseCase:
    """Provide a mocked GetCinemaMoviesUseCase."""
    return create_autospec(GetCinemaMoviesUseCase, instance=True)


@pytest.fixture
def mock_get_screenings_use_case() -> GetCinemaScreeningsUseCase:
    """Provide a mocked GetCinemaScreeningsUseCase."""
    return create_autospec(GetCinemaScreeningsUseCase, instance=True)


@pytest.fixture
def controller(
    mock_auth_controller: AuthController,
    mock_create_use_case: CreateCinemaUseCase,
    mock_delete_use_case: DeleteCinemaUseCase,
    mock_get_use_case: GetCinemaUseCase,
    mock_get_movies_use_case: GetCinemaMoviesUseCase,
    mock_get_screenings_use_case: GetCinemaScreeningsUseCase,
    mock_list_use_case: ListCinemasUseCase,
    mock_update_use_case: UpdateCinemaUseCase,
) -> CinemaController:
    """Provide a CinemaController wired to mocks."""
    return CinemaController(
        auth_controller=mock_auth_controller,
        create_cinema_use_case=mock_create_use_case,
        delete_cinema_use_case=mock_delete_use_case,
        get_cinema_use_case=mock_get_use_case,
        get_cinema_movies_use_case=mock_get_movies_use_case,
        get_cinema_screenings_use_case=mock_get_screenings_use_case,
        list_cinemas_use_case=mock_list_use_case,
        update_cinema_use_case=mock_update_use_case,
    )


@pytest.mark.asyncio
async def test_create_validates_admin_then_delegates_to_use_case(
    controller: CinemaController,
    mock_auth_controller: AuthController,
    mock_create_use_case: CreateCinemaUseCase,
) -> None:
    """Verify create validates admin, then delegates to the use case."""
    mock_auth_controller.validate_admin.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    expected_output = CreateCinemaUseCase.OutputData(
        id="cin-001",
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )
    mock_create_use_case.execute.return_value = expected_output

    result = await controller.create(
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )

    assert result == expected_output
    mock_auth_controller.validate_admin.assert_called_once_with()

    mock_create_use_case.execute.assert_awaited_once()
    input_data = mock_create_use_case.execute.call_args[0][0]
    assert isinstance(input_data, CreateCinemaUseCase.InputData)
    assert input_data.name == "Test Cinema"
    assert input_data.address == "123 Test St"


@pytest.mark.asyncio
async def test_create_raises_when_not_admin(
    controller: CinemaController,
    mock_auth_controller: AuthController,
    mock_create_use_case: CreateCinemaUseCase,
) -> None:
    """Verify create propagates ValueError when admin validation fails."""
    mock_auth_controller.validate_admin.side_effect = ValueError(
        "Access denied: admin role required."
    )

    with pytest.raises(ValueError, match="Access denied"):
        await controller.create(name="Test Cinema")

    mock_auth_controller.validate_admin.assert_called_once_with()
    mock_create_use_case.execute.assert_not_called()


@pytest.mark.asyncio
async def test_delete_validates_admin_then_delegates_to_use_case(
    controller: CinemaController,
    mock_auth_controller: AuthController,
    mock_delete_use_case: DeleteCinemaUseCase,
) -> None:
    """Verify delete validates admin, then delegates to the use case."""
    mock_auth_controller.validate_admin.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    expected_output = DeleteCinemaUseCase.OutputData(cinema_id="cin-001")
    mock_delete_use_case.execute.return_value = expected_output

    result = await controller.delete(cinema_id="cin-001")

    assert result == expected_output
    mock_auth_controller.validate_admin.assert_called_once_with()

    mock_delete_use_case.execute.assert_awaited_once()
    input_data = mock_delete_use_case.execute.call_args[0][0]
    assert isinstance(input_data, DeleteCinemaUseCase.InputData)
    assert input_data.cinema_id == "cin-001"


@pytest.mark.asyncio
async def test_delete_raises_when_not_admin(
    controller: CinemaController,
    mock_auth_controller: AuthController,
    mock_delete_use_case: DeleteCinemaUseCase,
) -> None:
    """Verify delete propagates ValueError when admin validation fails."""
    mock_auth_controller.validate_admin.side_effect = ValueError(
        "Access denied: admin role required."
    )

    with pytest.raises(ValueError, match="Access denied"):
        await controller.delete(cinema_id="cin-001")

    mock_auth_controller.validate_admin.assert_called_once_with()
    mock_delete_use_case.execute.assert_not_called()


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_returns_cinemas(
    controller: CinemaController,
    mock_list_use_case: ListCinemasUseCase,
) -> None:
    """Verify list returns cinema data from the use case."""
    cinema_data = [
        ListCinemasUseCase.CinemaData(
            id="cin-001",
            name="Cinema du Parc",
            address="123 Rue du Parc",
            city="Montreal",
            website="https://cinemaduparc.ca",
        ),
        ListCinemasUseCase.CinemaData(
            id="cin-002",
            name="Quartier Latin",
            address="345 Rue Ontario",
            city="Montreal",
        ),
    ]
    expected = ListCinemasUseCase.OutputData(cinemas=cinema_data, total=2)
    mock_list_use_case.execute.return_value = expected

    result = await controller.list()

    assert result == expected
    assert len(result.cinemas) == 2
    mock_list_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_passes_name_filter(
    controller: CinemaController,
    mock_list_use_case: ListCinemasUseCase,
) -> None:
    """Verify list passes the name filter to the use case."""
    output = ListCinemasUseCase.OutputData(cinemas=[], total=0)
    mock_list_use_case.execute.return_value = output

    await controller.list(name="Parc")

    mock_list_use_case.execute.assert_awaited_once()
    input_data = mock_list_use_case.execute.call_args[0][0]
    assert isinstance(input_data, ListCinemasUseCase.InputData)
    assert input_data.name == "Parc"


@pytest.mark.asyncio
async def test_list_passes_page_and_size(
    controller: CinemaController,
    mock_list_use_case: ListCinemasUseCase,
) -> None:
    """Verify list passes page/size through to the use case."""
    output = ListCinemasUseCase.OutputData(cinemas=[], total=0)
    mock_list_use_case.execute.return_value = output

    await controller.list(page=2, size=5)

    mock_list_use_case.execute.assert_awaited_once()
    input_data = mock_list_use_case.execute.call_args[0][0]
    assert input_data.page == 2
    assert input_data.size == 5


@pytest.mark.asyncio
async def test_list_does_not_check_auth(
    controller: CinemaController,
    mock_auth_controller: AuthController,
    mock_list_use_case: ListCinemasUseCase,
) -> None:
    """Verify list does not call validate_admin (public operation)."""
    output = ListCinemasUseCase.OutputData(cinemas=[], total=0)
    mock_list_use_case.execute.return_value = output

    await controller.list()

    mock_auth_controller.validate_admin.assert_not_called()


# ---------------------------------------------------------------------------
# list_cinemas (admin-gated variant)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_cinemas_validates_admin_then_delegates_to_use_case(
    controller: CinemaController,
    mock_auth_controller: AuthController,
    mock_list_use_case: ListCinemasUseCase,
) -> None:
    """Verify list_cinemas validates admin, then delegates to the use case."""
    mock_auth_controller.validate_admin.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    cinema_data = [
        ListCinemasUseCase.CinemaData(
            id="cin-001",
            name="Cinema du Parc",
        ),
    ]
    expected = ListCinemasUseCase.OutputData(cinemas=cinema_data, total=1)
    mock_list_use_case.execute.return_value = expected

    result = await controller.list_cinemas(name_filter="Parc")

    assert result == expected
    mock_auth_controller.validate_admin.assert_called_once_with()
    mock_list_use_case.execute.assert_awaited_once()
    input_data = mock_list_use_case.execute.call_args[0][0]
    assert input_data.name == "Parc"
    assert input_data.page == 1
    assert input_data.size is None


@pytest.mark.asyncio
async def test_list_cinemas_raises_when_not_admin(
    controller: CinemaController,
    mock_auth_controller: AuthController,
    mock_list_use_case: ListCinemasUseCase,
) -> None:
    """Verify list_cinemas propagates ValueError when admin validation fails."""
    mock_auth_controller.validate_admin.side_effect = ValueError(
        "Access denied: admin role required."
    )

    with pytest.raises(ValueError, match="Access denied"):
        await controller.list_cinemas()

    mock_auth_controller.validate_admin.assert_called_once_with()
    mock_list_use_case.execute.assert_not_called()


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_validates_admin_then_delegates_to_use_case(
    controller: CinemaController,
    mock_auth_controller: AuthController,
    mock_update_use_case: UpdateCinemaUseCase,
) -> None:
    """Verify update validates admin, then delegates to the use case."""
    mock_auth_controller.validate_admin.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    expected_output = UpdateCinemaUseCase.OutputData(
        id="cin-001",
        name="Updated Name",
        address="456 New Ave",
        city="Quebec",
        website="https://updated.example.com",
    )
    mock_update_use_case.execute.return_value = expected_output

    result = await controller.update(
        cinema_id="cin-001",
        name="Updated Name",
        address="456 New Ave",
        city="Quebec",
        website="https://updated.example.com",
    )

    assert result == expected_output
    mock_auth_controller.validate_admin.assert_called_once_with()

    mock_update_use_case.execute.assert_awaited_once()
    input_data = mock_update_use_case.execute.call_args[0][0]
    assert isinstance(input_data, UpdateCinemaUseCase.InputData)
    assert input_data.cinema_id == "cin-001"
    assert input_data.name == "Updated Name"
    assert input_data.address == "456 New Ave"
    assert input_data.city == "Quebec"
    assert input_data.website == "https://updated.example.com"


@pytest.mark.asyncio
async def test_update_raises_when_not_admin(
    controller: CinemaController,
    mock_auth_controller: AuthController,
    mock_update_use_case: UpdateCinemaUseCase,
) -> None:
    """Verify update propagates ValueError when admin validation fails."""
    mock_auth_controller.validate_admin.side_effect = ValueError(
        "Access denied: admin role required."
    )

    with pytest.raises(ValueError, match="Access denied"):
        await controller.update(cinema_id="cin-001", name="Updated Name")

    mock_auth_controller.validate_admin.assert_called_once_with()
    mock_update_use_case.execute.assert_not_called()
