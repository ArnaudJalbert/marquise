"""Tests for CLI commands using CliRunner and mocked Container."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from marquise.application.use_cases.delete_cinema import DeleteCinemaUseCase
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.infrastructure.controllers.auth_controller import AuthController
from marquise.infrastructure.controllers.cinema_controller import CinemaController
from marquise.interface_adapters.repositories.protocols.auth import AuthSession


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for Container creation."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "test-key")


@pytest.fixture
def mock_auth_controller() -> MagicMock:
    """Provide a mocked AuthController."""
    return create_autospec(AuthController, instance=True)


@pytest.fixture
def mock_container(mock_auth_controller: MagicMock) -> MagicMock:
    """Provide a mocked Container with a mocked auth_controller."""
    container = MagicMock()
    container.auth_controller = mock_auth_controller
    return container


# ---------------------------------------------------------------------------
# auth login
# ---------------------------------------------------------------------------


def test_auth_login_success_admin(
    mock_container: MagicMock,
    mock_auth_controller: MagicMock,
) -> None:
    """Verify auth login prints success message for admin users."""
    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    mock_auth_controller.login.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    with patch(
        "marquise.infrastructure.cli.auth_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["auth", "login"],
            input="admin@example.com\npassword123\n",
        )

    assert result.exit_code == 0
    assert "Logged in as admin@example.com (admin)" in result.stdout


def test_auth_login_success_non_admin(
    mock_container: MagicMock,
    mock_auth_controller: MagicMock,
) -> None:
    """Verify auth login warns non-admin users."""
    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    mock_auth_controller.login.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="user@example.com",
        is_admin=False,
    )

    with patch(
        "marquise.infrastructure.cli.auth_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["auth", "login"],
            input="user@example.com\npassword123\n",
        )

    assert result.exit_code == 0
    assert "does not have admin role" in result.stdout


def test_auth_login_failure(
    mock_container: MagicMock,
    mock_auth_controller: MagicMock,
) -> None:
    """Verify auth login shows error on failure and exits with code 1."""
    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    mock_auth_controller.login.side_effect = ValueError("Invalid credentials")

    with patch(
        "marquise.infrastructure.cli.auth_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["auth", "login"],
            input="bad@example.com\nwrong\n",
        )

    assert result.exit_code == 1
    assert "Login failed: Invalid credentials" in result.stderr


# ---------------------------------------------------------------------------
# auth logout
# ---------------------------------------------------------------------------


def test_auth_logout(
    mock_container: MagicMock,
    mock_auth_controller: MagicMock,
) -> None:
    """Verify auth logout calls controller.logout and prints message."""
    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with patch(
        "marquise.infrastructure.cli.auth_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["auth", "logout"])

    assert result.exit_code == 0
    assert "Logged out" in result.stdout
    mock_auth_controller.logout.assert_called_once_with()


# ---------------------------------------------------------------------------
# auth status
# ---------------------------------------------------------------------------


def test_auth_status_not_authenticated(
    mock_container: MagicMock,
    mock_auth_controller: MagicMock,
) -> None:
    """Verify auth status shows 'Not authenticated' when no session."""
    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    mock_auth_controller.status.return_value = None

    with patch(
        "marquise.infrastructure.cli.auth_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "Not authenticated" in result.stdout


def test_auth_status_expired_session(
    mock_container: MagicMock,
    mock_auth_controller: MagicMock,
) -> None:
    """Verify auth status shows expired message."""
    import time

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    mock_auth_controller.status.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=time.time() - 10,
        user_id="usr",
        email="user@example.com",
        is_admin=False,
    )

    with patch(
        "marquise.infrastructure.cli.auth_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "Session expired" in result.stdout
    assert "user@example.com" in result.stdout


def test_auth_status_authenticated_admin(
    mock_container: MagicMock,
    mock_auth_controller: MagicMock,
) -> None:
    """Verify auth status shows admin info."""
    import time

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    mock_auth_controller.status.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=time.time() + 3600,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )

    with patch(
        "marquise.infrastructure.cli.auth_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "Authenticated as admin@example.com (admin)" in result.stdout


def test_auth_status_authenticated_user(
    mock_container: MagicMock,
    mock_auth_controller: MagicMock,
) -> None:
    """Verify auth status shows user role."""
    import time

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    mock_auth_controller.status.return_value = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=time.time() + 3600,
        user_id="usr",
        email="user@example.com",
        is_admin=False,
    )

    with patch(
        "marquise.infrastructure.cli.auth_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["auth", "status"])

    assert result.exit_code == 0
    assert "Authenticated as user@example.com (user)" in result.stdout


# ---------------------------------------------------------------------------
# cinema create
# ---------------------------------------------------------------------------


def test_cinema_create_success(
    mock_container: MagicMock,
    mock_auth_controller: MagicMock,
) -> None:
    """Verify cinema create prints cinema details on success."""
    from marquise.application.use_cases.create_cinema import CreateCinemaUseCase

    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.create = AsyncMock(
        return_value=CreateCinemaUseCase.OutputData(
            id="cin-001",
            name="Test Cinema",
            address="123 Test St",
            city="Montreal",
            website="https://example.com",
        )
    )
    mock_container.cinema_controller = mock_cinema_controller
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with patch(
        "marquise.infrastructure.cli.cinema_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["cinema", "create"],
            input="Test Cinema\n123 Test St\nMontreal\nhttps://example.com\n",
        )

    assert result.exit_code == 0
    assert "Cinema created:" in result.stdout
    assert "cin-001" in result.stdout
    assert "Test Cinema" in result.stdout
    assert "123 Test St" in result.stdout
    assert "Montreal" in result.stdout
    assert "https://example.com" in result.stdout
    mock_container.initialize.assert_called_once()
    mock_container.shutdown.assert_called_once()


def test_cinema_create_failure(
    mock_container: MagicMock,
) -> None:
    """Verify cinema create shows error on failure."""

    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.create = AsyncMock(side_effect=ValueError("Admin required"))
    mock_container.cinema_controller = mock_cinema_controller
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with patch(
        "marquise.infrastructure.cli.cinema_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["cinema", "create"],
            input="Test Cinema\n123 Test St\nMontreal\nhttps://example.com\n",
        )

    assert result.exit_code == 1
    assert "Failed to create cinema: Admin required" in result.stderr
    assert "Created" not in result.stdout
    mock_container.initialize.assert_called_once()
    mock_container.shutdown.assert_called_once()


# ---------------------------------------------------------------------------
# cinema delete
# ---------------------------------------------------------------------------


def _make_cinema_data(
    cinema_id: str = "cin-001",
    name: str = "Test Cinema",
    address: str | None = "123 Test St",
    city: str | None = "Montreal",
    website: str | None = "https://example.com",
) -> ListCinemasUseCase.CinemaData:
    """Helper to build a CinemaData instance for test setup."""
    return ListCinemasUseCase.CinemaData(
        id=cinema_id,
        name=name,
        address=address,
        city=city,
        website=website,
    )


@pytest.fixture
def mock_cinema_controller_for_delete() -> MagicMock:
    """Provide a mocked CinemaController with list/delete methods."""
    controller = create_autospec(CinemaController, instance=True)
    controller.list_cinemas = AsyncMock()
    controller.delete = AsyncMock()
    return controller


@pytest.fixture
def mock_cinema_controller_for_update() -> MagicMock:
    """Provide a mocked CinemaController with list/update methods."""
    controller = create_autospec(CinemaController, instance=True)
    controller.list_cinemas = AsyncMock()
    controller.update = AsyncMock()
    return controller


def test_cinema_delete_success(
    mock_container: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
) -> None:
    """Verify cinema delete succeeds with valid selection and name confirmation."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    cinema = _make_cinema_data()
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[cinema])
    )
    mock_cinema_controller_for_delete.delete.return_value = (
        DeleteCinemaUseCase.OutputData(cinema_id="cin-001")
    )
    mock_container.cinema_controller = mock_cinema_controller_for_delete
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Test Cinema")

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "delete"])

    assert result.exit_code == 0
    assert 'Cinema "Test Cinema" (ID: cin-001) deleted.' in result.stdout
    mock_container.initialize.assert_called_once()
    mock_container.shutdown.assert_called_once()
    mock_cinema_controller_for_delete.delete.assert_awaited_once_with(
        cinema_id="cin-001",
    )


def test_cinema_delete_name_mismatch(
    mock_container: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
) -> None:
    """Verify cinema delete aborts when confirmation name does not match."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[_make_cinema_data()])
    )
    mock_container.cinema_controller = mock_cinema_controller_for_delete
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=_make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Wrong Name")

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "delete"])

    assert result.exit_code == 1
    assert 'Name mismatch: expected "Test Cinema", got "Wrong Name"' in result.stderr
    mock_cinema_controller_for_delete.delete.assert_not_awaited()
    mock_container.shutdown.assert_called_once()


def test_cinema_delete_no_cinemas(
    mock_container: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
) -> None:
    """Verify cinema delete shows message when no cinemas exist."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[])
    )
    mock_container.cinema_controller = mock_cinema_controller_for_delete
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with patch(
        "marquise.infrastructure.cli.cinema_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "delete"])

    assert result.exit_code == 0
    assert "No cinemas available to delete." in result.stdout
    mock_cinema_controller_for_delete.delete.assert_not_awaited()


def test_cinema_delete_cancelled_at_select(
    mock_container: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
) -> None:
    """Verify cinema delete handles cancellation at the selection prompt."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[_make_cinema_data()])
    )
    mock_container.cinema_controller = mock_cinema_controller_for_delete
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value="__exit__")

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "delete"])

    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_cinema_controller_for_delete.delete.assert_not_awaited()


def test_cinema_delete_cancelled_at_confirmation(
    mock_container: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
) -> None:
    """Verify cinema delete handles cancellation at the confirmation prompt."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[_make_cinema_data()])
    )
    mock_container.cinema_controller = mock_cinema_controller_for_delete
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=_make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value=None)

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "delete"])

    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_cinema_controller_for_delete.delete.assert_not_awaited()


def test_cinema_delete_failure(
    mock_container: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
) -> None:
    """Verify cinema delete shows error when the use case fails."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[_make_cinema_data()])
    )
    mock_cinema_controller_for_delete.delete = AsyncMock(
        side_effect=ValueError("Something went wrong"),
    )
    mock_container.cinema_controller = mock_cinema_controller_for_delete
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=_make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Test Cinema")

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "delete"])

    assert result.exit_code == 1
    assert "Failed to delete cinema: Something went wrong" in result.stderr


# ---------------------------------------------------------------------------
# cinema list
# ---------------------------------------------------------------------------


def _make_list_mock_cinemas() -> list:
    """Build sample cinema data for list tests."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    return [
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


def test_cinema_list_success(
    mock_container: MagicMock,
) -> None:
    """Verify cinema list prints cinema names."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    cinemas = _make_list_mock_cinemas()
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=cinemas)
    )
    mock_container.cinema_controller = mock_cinema_controller
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with patch(
        "marquise.infrastructure.cli.cinema_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "list"])

    assert result.exit_code == 0
    assert "Available cinemas:" in result.stdout
    assert "Cinema du Parc" in result.stdout
    assert "Quartier Latin" in result.stdout
    mock_container.initialize.assert_called_once()
    mock_container.shutdown.assert_called_once()


def test_cinema_list_empty(
    mock_container: MagicMock,
) -> None:
    """Verify cinema list shows 'No cinemas found' when empty."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=[])
    )
    mock_container.cinema_controller = mock_cinema_controller
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with patch(
        "marquise.infrastructure.cli.cinema_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "list"])

    assert result.exit_code == 0
    assert "No cinemas found." in result.stdout
    mock_container.initialize.assert_called_once()
    mock_container.shutdown.assert_called_once()


def test_cinema_list_failure(
    mock_container: MagicMock,
) -> None:
    """Verify cinema list shows error on failure."""
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        side_effect=ValueError("Something went wrong")
    )
    mock_container.cinema_controller = mock_cinema_controller
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with patch(
        "marquise.infrastructure.cli.cinema_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "list"])

    assert result.exit_code == 1
    assert "Failed to list cinemas: Something went wrong" in result.stderr
    mock_container.initialize.assert_called_once()
    mock_container.shutdown.assert_called_once()


def test_cinema_list_verbose(
    mock_container: MagicMock,
) -> None:
    """Verify cinema list --verbose shows detailed table."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    cinemas = _make_list_mock_cinemas()
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=cinemas)
    )
    mock_container.cinema_controller = mock_cinema_controller
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with patch(
        "marquise.infrastructure.cli.cinema_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "list", "--verbose"])

    assert result.exit_code == 0
    assert "Available cinemas:" in result.stdout
    assert "cin-001" in result.stdout
    assert "123 Rue du Parc" in result.stdout
    assert "cin-002" in result.stdout
    assert "345 Rue Ontario" in result.stdout
    assert "cinemaduparc" in result.stdout
    mock_container.initialize.assert_called_once()
    mock_container.shutdown.assert_called_once()


def test_cinema_list_with_name_filter(
    mock_container: MagicMock,
) -> None:
    """Verify cinema list --name passes filter to controller."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=[])
    )
    mock_container.cinema_controller = mock_cinema_controller
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with patch(
        "marquise.infrastructure.cli.cinema_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "list", "--name", "Parc"])

    assert result.exit_code == 0
    mock_cinema_controller.list.assert_called_once_with(name="Parc")
    mock_container.initialize.assert_called_once()
    mock_container.shutdown.assert_called_once()


# ---------------------------------------------------------------------------
# cinema update
# ---------------------------------------------------------------------------


def test_cinema_update_success(
    mock_container: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
) -> None:
    """Verify cinema update succeeds when selecting fields and providing values."""
    from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase

    cinema = _make_cinema_data()
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[cinema])
    )
    mock_cinema_controller_for_update.update.return_value = (
        UpdateCinemaUseCase.OutputData(
            id="cin-001",
            name="Updated Name",
            address="456 New Ave",
            city="Montreal",
            website="https://example.com",
        )
    )
    mock_container.cinema_controller = mock_cinema_controller_for_update
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["name", "address"]
        )
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=["Updated Name", "456 New Ave"]
        )

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "update"])

    assert result.exit_code == 0
    assert "Cinema updated:" in result.stdout
    assert "Updated Name" in result.stdout
    assert "456 New Ave" in result.stdout
    mock_container.initialize.assert_called_once()
    mock_container.shutdown.assert_called_once()
    mock_cinema_controller_for_update.update.assert_awaited_once_with(
        cinema_id="cin-001",
        name="Updated Name",
        address="456 New Ave",
        city="Montreal",
        website="https://example.com",
    )


def test_cinema_update_single_field(
    mock_container: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
) -> None:
    """Verify cinema update only changes the selected fields."""
    from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase

    cinema = _make_cinema_data()
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[cinema])
    )
    mock_cinema_controller_for_update.update.return_value = (
        UpdateCinemaUseCase.OutputData(
            id="cin-001",
            name="Renamed",
            address="123 Test St",
            city="Montreal",
            website="https://example.com",
        )
    )
    mock_container.cinema_controller = mock_cinema_controller_for_update
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["name"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Renamed")

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "update"])

    assert result.exit_code == 0
    assert "Cinema updated:" in result.stdout
    mock_container.initialize.assert_called_once()
    mock_container.shutdown.assert_called_once()
    mock_cinema_controller_for_update.update.assert_awaited_once_with(
        cinema_id="cin-001",
        name="Renamed",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )


def test_cinema_update_clear_optional_field(
    mock_container: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
) -> None:
    """Verify cinema update allows clearing an optional field to None."""
    from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase

    cinema = _make_cinema_data()
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[cinema])
    )
    mock_cinema_controller_for_update.update.return_value = (
        UpdateCinemaUseCase.OutputData(
            id="cin-001",
            name="Test Cinema",
            city="Montreal",
            website="https://example.com",
        )
    )
    mock_container.cinema_controller = mock_cinema_controller_for_update
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["address"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value="")

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "update"])

    assert result.exit_code == 0
    assert "Cinema updated:" in result.stdout
    mock_cinema_controller_for_update.update.assert_awaited_once_with(
        cinema_id="cin-001",
        name="Test Cinema",
        address=None,
        city="Montreal",
        website="https://example.com",
    )


def test_cinema_update_no_cinemas(
    mock_container: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
) -> None:
    """Verify cinema update shows message when no cinemas exist."""
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[])
    )
    mock_container.cinema_controller = mock_cinema_controller_for_update
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with patch(
        "marquise.infrastructure.cli.cinema_commands.Container",
        return_value=mock_container,
    ):
        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "update"])

    assert result.exit_code == 0
    assert "No cinemas available to update." in result.stdout
    mock_cinema_controller_for_update.update.assert_not_awaited()


def test_cinema_update_cancelled_at_select(
    mock_container: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
) -> None:
    """Verify cinema update handles cancellation at the selection prompt."""
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[_make_cinema_data()])
    )
    mock_container.cinema_controller = mock_cinema_controller_for_update
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value="__exit__")

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "update"])

    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_cinema_controller_for_update.update.assert_not_awaited()


def test_cinema_update_cancelled_at_fields(
    mock_container: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
) -> None:
    """Verify cinema update handles cancellation at the fields checkbox."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    cinema = _make_cinema_data()
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[cinema])
    )
    mock_container.cinema_controller = mock_cinema_controller_for_update
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=[])

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "update"])

    assert result.exit_code == 0
    assert "No fields selected. Cancelled." in result.stdout
    mock_cinema_controller_for_update.update.assert_not_awaited()


def test_cinema_update_failure(
    mock_container: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
) -> None:
    """Verify cinema update shows error when use case fails."""
    from marquise.application.use_cases.list_cinemas import ListCinemasUseCase

    cinema = _make_cinema_data()
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[cinema])
    )
    mock_cinema_controller_for_update.update.side_effect = ValueError(
        "Something went wrong"
    )
    mock_container.cinema_controller = mock_cinema_controller_for_update
    mock_container.initialize = AsyncMock()
    mock_container.shutdown = AsyncMock()

    from typer.testing import CliRunner

    from marquise.infrastructure.cli.app import app

    with (
        patch(
            "marquise.infrastructure.cli.cinema_commands.Container",
            return_value=mock_container,
        ),
        patch("marquise.infrastructure.cli.cinema_commands.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["name"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value="New Name")

        runner = CliRunner()
        result = runner.invoke(app, ["cinema", "update"])

    assert result.exit_code == 1
    assert "Failed to update cinema" in result.stderr
    assert "Something went wrong" in result.stderr
