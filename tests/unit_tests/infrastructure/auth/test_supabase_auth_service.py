"""Tests for SupabaseAuthService."""

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from marquise.infrastructure.auth.supabase_auth_service import (
    SupabaseAuthService,
)
from marquise.interface_adapters.repositories.protocols.auth import AuthSession


@pytest.fixture
def mock_client() -> MagicMock:
    """Provide a mocked Supabase client."""
    return MagicMock()


@pytest.fixture
def service(
    mock_client: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> SupabaseAuthService:
    """Provide a SupabaseAuthService with mocked client."""
    import marquise.infrastructure.auth.supabase_auth_service as svc_mod

    monkeypatch.setattr(
        svc_mod, "create_client", lambda supabase_url, supabase_key: mock_client
    )
    return SupabaseAuthService(
        supabase_url="https://test.supabase.co",
        publishable_key="test-key",
    )


@pytest.fixture
def tmp_session_dir(
    service: SupabaseAuthService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Redirect session file to a temporary directory."""
    session_dir = tmp_path / ".marquise"
    session_dir.mkdir()
    monkeypatch.setattr(
        "marquise.infrastructure.auth.supabase_auth_service.AUTH_DIR", session_dir
    )
    monkeypatch.setattr(
        "marquise.infrastructure.auth.supabase_auth_service.SESSION_FILE",
        session_dir / "auth.json",
    )
    return session_dir


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------


def _make_mock_user(role: str = "admin", email: str = "admin@example.com") -> MagicMock:
    """Build a mock user object with the given role."""
    user = MagicMock()
    user.id = "usr-123"
    user.email = email
    user.app_metadata = {"role": role}
    return user


def _make_mock_session() -> MagicMock:
    """Build a mock session object."""
    session = MagicMock()
    session.access_token = "tok-abc"
    session.refresh_token = "ref-xyz"
    session.expires_at = time.time() + 3600
    return session


def test_login_success(service: SupabaseAuthService, mock_client: MagicMock) -> None:
    """Verify login returns an AuthSession on success."""
    mock_user = _make_mock_user()
    mock_sesh = _make_mock_session()

    auth_result = MagicMock()
    auth_result.user = mock_user
    auth_result.session = mock_sesh
    mock_client.auth.sign_in_with_password.return_value = auth_result

    result = service.login(email="admin@example.com", password="pwd")

    assert isinstance(result, AuthSession)
    assert result.access_token == "tok-abc"
    assert result.refresh_token == "ref-xyz"
    assert result.user_id == "usr-123"
    assert result.email == "admin@example.com"
    assert result.is_admin is True
    mock_client.auth.sign_in_with_password.assert_called_once_with(
        {"email": "admin@example.com", "password": "pwd"}
    )


def test_login_failure_no_user(
    service: SupabaseAuthService, mock_client: MagicMock
) -> None:
    """Verify login raises ValueError when user is None."""
    auth_result = MagicMock()
    auth_result.user = None
    auth_result.session = None
    mock_client.auth.sign_in_with_password.return_value = auth_result

    with pytest.raises(ValueError, match="Authentication failed"):
        service.login(email="bad@example.com", password="wrong")


def test_login_marks_non_admin(
    service: SupabaseAuthService, mock_client: MagicMock
) -> None:
    """Verify login sets is_admin=False when role is not admin."""
    mock_user = _make_mock_user(role="user")
    mock_sesh = _make_mock_session()

    auth_result = MagicMock()
    auth_result.user = mock_user
    auth_result.session = mock_sesh
    mock_client.auth.sign_in_with_password.return_value = auth_result

    result = service.login(email="user@example.com", password="pwd")

    assert result.is_admin is False


def test_login_persists_session(
    service: SupabaseAuthService,
    mock_client: MagicMock,
    tmp_session_dir: Path,
) -> None:
    """Verify login writes session data to disk."""
    mock_user = _make_mock_user()
    mock_sesh = _make_mock_session()

    auth_result = MagicMock()
    auth_result.user = mock_user
    auth_result.session = mock_sesh
    mock_client.auth.sign_in_with_password.return_value = auth_result

    service.login(email="admin@example.com", password="pwd")

    session_file = tmp_session_dir / "auth.json"
    assert session_file.exists()
    data = json.loads(session_file.read_text())
    assert data["access_token"] == "tok-abc"
    assert data["is_admin"] is True


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


def test_logout_clears_session(
    service: SupabaseAuthService,
    mock_client: MagicMock,
    tmp_session_dir: Path,
) -> None:
    """Verify logout calls sign_out and removes session file."""
    session_file = tmp_session_dir / "auth.json"
    session_file.write_text('{"access_token": "tok"}')
    assert session_file.exists()

    service.logout()

    mock_client.auth.sign_out.assert_called_once_with()
    assert not session_file.exists()


# ---------------------------------------------------------------------------
# get_validated_session
# ---------------------------------------------------------------------------


def test_get_validated_session_valid(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify get_validated_session returns session when valid."""
    session_file = tmp_session_dir / "auth.json"
    session_file.write_text(
        json.dumps(
            {
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_at": time.time() + 3600,
                "user_id": "usr",
                "email": "admin@example.com",
                "is_admin": True,
            }
        )
    )

    result = service.get_validated_session()

    assert result.email == "admin@example.com"
    assert result.is_admin is True


def test_get_validated_session_no_session(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify get_validated_session raises ValueError when no session file."""
    with pytest.raises(ValueError, match="Not authenticated"):
        service.get_validated_session()


def test_get_validated_session_expired_and_refresh_succeeds(
    service: SupabaseAuthService,
    mock_client: MagicMock,
    tmp_session_dir: Path,
) -> None:
    """Verify get_validated_session refreshes an expired session."""
    session_file = tmp_session_dir / "auth.json"
    session_file.write_text(
        json.dumps(
            {
                "access_token": "tok-old",
                "refresh_token": "ref-xyz",
                "expires_at": time.time() - 10,
                "user_id": "usr",
                "email": "admin@example.com",
                "is_admin": True,
            }
        )
    )

    # Mock successful refresh
    mock_user = _make_mock_user()
    mock_sesh = _make_mock_session()
    mock_sesh.access_token = "tok-new"
    refresh_result = MagicMock()
    refresh_result.user = mock_user
    refresh_result.session = mock_sesh
    mock_client.auth.refresh_session.return_value = refresh_result

    result = service.get_validated_session()

    assert result.access_token == "tok-new"
    mock_client.auth.refresh_session.assert_called_once_with("ref-xyz")


def test_get_validated_session_expired_and_refresh_fails(
    service: SupabaseAuthService,
    mock_client: MagicMock,
    tmp_session_dir: Path,
) -> None:
    """Verify get_validated_session raises ValueError when refresh fails."""
    session_file = tmp_session_dir / "auth.json"
    session_file.write_text(
        json.dumps(
            {
                "access_token": "tok-old",
                "refresh_token": "ref-xyz",
                "expires_at": time.time() - 10,
                "user_id": "usr",
                "email": "admin@example.com",
                "is_admin": True,
            }
        )
    )

    mock_client.auth.refresh_session.side_effect = Exception("Network error")

    with pytest.raises(ValueError, match="Session expired and refresh failed"):
        service.get_validated_session()


def test_get_validated_session_not_admin(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify get_validated_session raises ValueError when user is not admin."""
    session_file = tmp_session_dir / "auth.json"
    session_file.write_text(
        json.dumps(
            {
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_at": time.time() + 3600,
                "user_id": "usr",
                "email": "user@example.com",
                "is_admin": False,
            }
        )
    )

    with pytest.raises(ValueError, match="Access denied"):
        service.get_validated_session()


# ---------------------------------------------------------------------------
# get_session_status
# ---------------------------------------------------------------------------


def test_get_session_status_returns_session(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify get_session_status returns the cached session."""
    session_file = tmp_session_dir / "auth.json"
    session_file.write_text(
        json.dumps(
            {
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_at": 1_000_000.0,
                "user_id": "usr",
                "email": "user@example.com",
                "is_admin": False,
            }
        )
    )

    result = service.get_session_status()

    assert result is not None
    assert result.email == "user@example.com"


def test_get_session_status_returns_none(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify get_session_status returns None when no session file exists."""
    result = service.get_session_status()

    assert result is None


# ---------------------------------------------------------------------------
# session persistence helpers (tested directly)
# ---------------------------------------------------------------------------


def test_save_session_persists_to_disk(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify _save_session writes session data as JSON."""
    session = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=1_000_000.0,
        user_id="usr",
        email="test@example.com",
        is_admin=True,
    )

    service._save_session(session)

    session_file = tmp_session_dir / "auth.json"
    assert session_file.exists()
    data = json.loads(session_file.read_text())
    assert data["email"] == "test@example.com"
    assert data["is_admin"] is True


def test_load_session_reads_from_disk(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify _load_session reads session data from disk."""
    session_file = tmp_session_dir / "auth.json"
    session_file.write_text(
        json.dumps(
            {
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_at": 1_000_000.0,
                "user_id": "usr",
                "email": "test@example.com",
                "is_admin": True,
            }
        )
    )

    result = service._load_session()

    assert result is not None
    assert result.email == "test@example.com"
    assert result.is_admin is True


def test_load_session_returns_none_when_no_file(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify _load_session returns None when session file does not exist."""
    result = service._load_session()
    assert result is None


def test_load_session_returns_none_on_corrupt_json(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify _load_session returns None when session file contains invalid JSON."""
    session_file = tmp_session_dir / "auth.json"
    session_file.write_text("not valid json")

    result = service._load_session()
    assert result is None


def test_load_session_returns_none_on_missing_keys(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify _load_session returns None when session data is missing required keys."""
    session_file = tmp_session_dir / "auth.json"
    session_file.write_text('{"access_token": "tok"}')

    result = service._load_session()
    assert result is None


def test_clear_session_removes_file(
    service: SupabaseAuthService, tmp_session_dir: Path
) -> None:
    """Verify _clear_session deletes the session file."""
    session_file = tmp_session_dir / "auth.json"
    session_file.write_text("{}")
    assert session_file.exists()

    service._clear_session()

    assert not session_file.exists()


def test_clear_session_no_file(
    service: SupabaseAuthService,
) -> None:
    """Verify _clear_session does not raise when no session file exists."""
    service._clear_session()
