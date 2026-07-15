"""Tests for AuthSession value object and AuthService protocol."""

from __future__ import annotations

import time

import pytest

from marquise.interface_adapters.repositories.protocols.auth import (
    AuthService,
    AuthSession,
)


def test_auth_session_creation() -> None:
    """Verify AuthSession can be created with all fields."""
    session = AuthSession(
        access_token="tok-123",
        refresh_token="ref-456",
        expires_at=1_000_000.0,
        user_id="usr-789",
        email="test@example.com",
        is_admin=True,
    )
    assert session.access_token == "tok-123"
    assert session.refresh_token == "ref-456"
    assert session.expires_at == 1_000_000.0
    assert session.user_id == "usr-789"
    assert session.email == "test@example.com"
    assert session.is_admin is True


def test_auth_session_is_expired_returns_true() -> None:
    """Verify is_expired returns True when time >= expires_at."""
    past = time.time() - 10
    session = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=past,
        user_id="usr",
        email="test@example.com",
        is_admin=False,
    )
    assert session.is_expired


def test_auth_session_is_expired_returns_false() -> None:
    """Verify is_expired returns False when time < expires_at."""
    future = time.time() + 3600
    session = AuthSession(
        access_token="tok",
        refresh_token="ref",
        expires_at=future,
        user_id="usr",
        email="test@example.com",
        is_admin=False,
    )
    assert not session.is_expired


def test_auth_service_is_protocol() -> None:
    """Verify AuthService is a Protocol (cannot be instantiated directly)."""
    with pytest.raises(TypeError):
        AuthService()  # type: ignore[abstract]
