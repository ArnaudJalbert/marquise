"""Supabase authentication service for CLI sessions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from supabase import create_client

from marquise.interface_adapters.repositories.protocols.auth import AuthSession

AUTH_DIR = Path.home() / ".marquise"
SESSION_FILE = AUTH_DIR / "auth.json"


class SupabaseAuthService:
    """Handles Supabase authentication for the CLI.

    Wraps the Supabase Auth API for email/password sign-in, admin role
    verification, and local session persistence.
    """

    def __init__(self, supabase_url: str, publishable_key: str) -> None:
        self._client = create_client(
            supabase_url=supabase_url,
            supabase_key=publishable_key,
        )

    def login(self, email: str, password: str) -> AuthSession:
        """Authenticate with Supabase and return a session.

        Args:
            email: User's email address.
            password: User's password.

        Returns:
            An AuthSession with token and admin status.

        Raises:
            ValueError: If authentication fails or user is not an admin.
        """
        result = self._client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        user = result.user
        session = result.session

        if user is None or session is None:
            raise ValueError("Authentication failed")

        is_admin = user.app_metadata.get("role") == "admin"

        auth_session = AuthSession(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_at=session.expires_at,
            user_id=user.id,
            email=user.email or email,
            is_admin=is_admin,
        )

        self._save_session(auth_session)
        return auth_session

    def get_validated_session(self) -> AuthSession:
        """Load the cached session and validate it.

        Reads session from ``~/.marquise/auth.json``, checks expiry and
        admin status.

        Returns:
            A valid AuthSession.

        Raises:
            ValueError: If no session exists, it's expired, or user is not
                an admin.
        """
        session = self._load_session()
        if session is None:
            raise ValueError(
                "Not authenticated. Please run 'marquise auth login' first."
            )
        if session.is_expired:
            try:
                session = self._refresh_session(session)
            except Exception:
                raise ValueError(
                    "Session expired and refresh failed. "
                    "Please run 'marquise auth login' again."
                )
        if not session.is_admin:
            raise ValueError(
                "Access denied: admin role required. "
                "Contact your Supabase project admin."
            )
        return session

    def logout(self) -> None:
        """Clear the cached session."""
        self._client.auth.sign_out()
        self._clear_session()

    def get_session_status(self) -> Optional[AuthSession]:
        """Return the current cached session without validation.

        Returns:
            The cached AuthSession, or None if no session file exists.
        """
        return self._load_session()

    def _save_session(self, session: AuthSession) -> None:
        AUTH_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at,
            "user_id": session.user_id,
            "email": session.email,
            "is_admin": session.is_admin,
        }
        SESSION_FILE.write_text(json.dumps(data, indent=2))

    def _load_session(self) -> Optional[AuthSession]:
        if not SESSION_FILE.exists():
            return None
        try:
            data = json.loads(SESSION_FILE.read_text())
            return AuthSession(**data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def _clear_session(self) -> None:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()

    def _refresh_session(self, session: AuthSession) -> AuthSession:
        result = self._client.auth.refresh_session(session.refresh_token)
        user = result.user
        new_session = result.session

        if user is None or new_session is None:
            raise ValueError("Session refresh failed")

        is_admin = user.app_metadata.get("role") == "admin"

        refreshed = AuthSession(
            access_token=new_session.access_token,
            refresh_token=new_session.refresh_token,
            expires_at=new_session.expires_at,
            user_id=user.id,
            email=user.email or session.email,
            is_admin=is_admin,
        )

        self._save_session(refreshed)
        return refreshed
