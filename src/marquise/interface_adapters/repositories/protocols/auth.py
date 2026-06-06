"""Auth service protocol."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class AuthSession:
    """Represents an authenticated session."""

    access_token: str
    refresh_token: str
    expires_at: float
    user_id: str
    email: str
    is_admin: bool

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class AuthService(Protocol):
    """Protocol for authentication services.

    Implementations handle credential verification, token management, and
    session persistence.  All methods are synchronous.
    """

    def login(self, email: str, password: str) -> AuthSession:
        """Authenticate with credentials.

        Args:
            email: User's email address.
            password: User's password.

        Returns:
            An AuthSession with token and admin status.

        Raises:
            ValueError: If authentication fails.
        """
        ...

    def get_validated_session(self) -> AuthSession:
        """Load the cached session and validate it.

        Checks expiry and admin status.

        Returns:
            A valid AuthSession.

        Raises:
            ValueError: If no session exists, it's expired, or user is not
                an admin.
        """
        ...

    def logout(self) -> None:
        """Clear the cached session."""
        ...

    def get_session_status(self) -> Optional[AuthSession]:
        """Return the current cached session without validation.

        Returns:
            The cached AuthSession, or None if no session file exists.
        """
        ...
