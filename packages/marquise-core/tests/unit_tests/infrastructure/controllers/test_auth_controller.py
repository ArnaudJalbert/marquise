"""Tests for AuthController."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.infrastructure.controllers.auth_controller import AuthController
from marquise.interface_adapters.repositories.protocols.auth import (
    AuthService,
    AuthSession,
)


@pytest.fixture
def mock_auth_service() -> AuthService:
    """Provide a mocked AuthService."""
    return create_autospec(AuthService, instance=True)


@pytest.fixture
def controller(mock_auth_service: AuthService) -> AuthController:
    """Provide an AuthController wired to the mock service."""
    return AuthController(auth_service=mock_auth_service)


def test_login_delegates(
    controller: AuthController, mock_auth_service: AuthService
) -> None:
    """Verify login delegates to the auth service."""
    expected = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=1_000_000.0,
        user_id="usr",
        email="a@b.com",
        is_admin=True,
    )
    mock_auth_service.login.return_value = expected  # type: ignore[attr-defined]

    result = controller.login(email="a@b.com", password="pwd")

    assert result == expected
    mock_auth_service.login.assert_called_once_with(  # type: ignore[attr-defined]
        email="a@b.com", password="pwd"
    )


def test_logout_delegates(
    controller: AuthController, mock_auth_service: AuthService
) -> None:
    """Verify logout delegates to the auth service."""
    controller.logout()

    mock_auth_service.logout.assert_called_once_with()  # type: ignore[attr-defined]


def test_status_delegates(
    controller: AuthController, mock_auth_service: AuthService
) -> None:
    """Verify status delegates to the auth service."""
    expected = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=1_000_000.0,
        user_id="usr",
        email="a@b.com",
        is_admin=False,
    )
    mock_auth_service.get_session_status.return_value = expected  # type: ignore[attr-defined]

    result = controller.status()

    assert result == expected
    mock_auth_service.get_session_status.assert_called_once_with()  # type: ignore[attr-defined]


def test_validate_admin_delegates(
    controller: AuthController, mock_auth_service: AuthService
) -> None:
    """Verify validate_admin delegates to the auth service."""
    expected = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )
    mock_auth_service.get_validated_session.return_value = expected  # type: ignore[attr-defined]

    result = controller.validate_admin()

    assert result == expected
    mock_auth_service.get_validated_session.assert_called_once_with()  # type: ignore[attr-defined]


def test_validate_admin_auto_login_from_env(
    controller: AuthController,
    mock_auth_service: AuthService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify validate_admin tries env var login when session is missing."""
    expected = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=9_999_999.0,
        user_id="usr",
        email="admin@example.com",
        is_admin=True,
    )
    mock_auth_service.get_validated_session.side_effect = [  # type: ignore[attr-defined]
        ValueError("no session"),
        expected,
    ]
    mock_auth_service.login.return_value = expected  # type: ignore[attr-defined]

    monkeypatch.setenv("MARQUISE_EMAIL", "admin@example.com")
    monkeypatch.setenv("MARQUISE_PASSWORD", "s3cret")

    result = controller.validate_admin()

    assert result == expected
    mock_auth_service.login.assert_called_once_with(  # type: ignore[attr-defined]
        email="admin@example.com", password="s3cret"
    )
    assert mock_auth_service.get_validated_session.call_count == 2  # type: ignore[attr-defined]


def test_validate_admin_auto_login_env_missing(
    controller: AuthController,
    mock_auth_service: AuthService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify validate_admin raises when session is missing and env not set."""
    monkeypatch.delenv("MARQUISE_EMAIL", raising=False)
    monkeypatch.delenv("MARQUISE_PASSWORD", raising=False)

    mock_auth_service.get_validated_session.side_effect = ValueError(  # type: ignore[attr-defined]
        "Not authenticated"
    )

    with pytest.raises(ValueError, match="Not authenticated"):
        controller.validate_admin()

    mock_auth_service.login.assert_not_called()  # type: ignore[attr-defined]


def test_validate_admin_auto_login_failure(
    controller: AuthController,
    mock_auth_service: AuthService,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify validate_admin raises when both session and env login fail."""
    mock_auth_service.get_validated_session.side_effect = ValueError(  # type: ignore[attr-defined]
        "Not authenticated"
    )
    mock_auth_service.login.side_effect = ValueError("Invalid credentials")  # type: ignore[attr-defined]

    monkeypatch.setenv("MARQUISE_EMAIL", "admin@example.com")
    monkeypatch.setenv("MARQUISE_PASSWORD", "wrong")

    with pytest.raises(ValueError, match="Not authenticated"):
        controller.validate_admin()

    mock_auth_service.login.assert_called_once_with(  # type: ignore[attr-defined]
        email="admin@example.com", password="wrong"
    )
