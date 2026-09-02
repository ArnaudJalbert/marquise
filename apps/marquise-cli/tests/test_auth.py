"""Tests for Supabase auth helpers."""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch

import pytest

from marquise_cli.auth.client import AuthClient, AuthError
from marquise_cli.auth.config import AuthSettings, load_auth_settings
from marquise_cli.auth.store import validate_role_name


def test_validate_role_name_normalizes_and_accepts_slug() -> None:
    assert validate_role_name(" Admin ") == "admin"
    assert validate_role_name("editor-in-chief") == "editor-in-chief"


@pytest.mark.parametrize("name", ["", "1bad", "Has Space", "a" * 65])
def test_validate_role_name_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValueError):
        validate_role_name(name)


def test_load_auth_settings_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co/")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost/db")
    monkeypatch.setenv("DATABASE_SCHEMA", "marquise-test")

    settings = load_auth_settings()

    assert settings == AuthSettings(
        supabase_url="https://example.supabase.co",
        service_role_key="service-key",
        database_url="postgresql://u:p@localhost/db",
        schema="marquise-test",
    )


def test_load_auth_settings_reports_missing_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        load_auth_settings()


def test_auth_client_create_user_parses_response() -> None:
    payload = {
        "id": "user-123",
        "email": "user@example.com",
        "created_at": "2026-01-01T00:00:00Z",
    }
    client = AuthClient("https://example.supabase.co", "service-key")

    with patch("urllib.request.urlopen") as urlopen:
        urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
            payload
        ).encode()
        user = client.create_user(email="user@example.com", password="secret")

    assert user.id == "user-123"
    assert user.email == "user@example.com"


def test_auth_client_raises_auth_error_on_http_failure() -> None:
    import urllib.error

    client = AuthClient("https://example.supabase.co", "service-key")
    error = urllib.error.HTTPError(
        url="https://example.supabase.co/auth/v1/admin/users",
        code=422,
        msg="Unprocessable Entity",
        hdrs=None,
        fp=BytesIO(b'{"message":"User already registered"}'),
    )

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(AuthError, match="User already registered"):
            client.create_user(email="user@example.com", password="secret")
