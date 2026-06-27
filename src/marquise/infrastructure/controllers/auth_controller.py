"""Controller for authentication operations."""

from __future__ import annotations

import os

from marquise.interface_adapters.repositories.protocols.auth import (
    AuthService,
    AuthSession,
)

MARQUISE_EMAIL_ENV_VAR = "MARQUISE_EMAIL"
MARQUISE_PASSWORD_ENV_VAR = "MARQUISE_PASSWORD"


class AuthController:
    """Handles authentication flows.

    Depends on the ``AuthService`` protocol — swap the concrete
    implementation in the container without touching this file.
    """

    def __init__(self, auth_service: AuthService) -> None:
        self._auth = auth_service

    def login(self, email: str, password: str) -> AuthSession:
        return self._auth.login(email=email, password=password)

    def logout(self) -> None:
        self._auth.logout()

    def status(self) -> AuthSession | None:
        return self._auth.get_session_status()

    def validate_admin(self) -> AuthSession:
        """Validate admin session, falling back to env var auto-login.

        Tries the cached session first.  If it doesn't exist or is expired,
        attempts to login from ``MARQUISE_EMAIL`` / ``MARQUISE_PASSWORD``
        environment variables.  Raises ``ValueError`` on failure.
        """
        try:
            return self._auth.get_validated_session()
        except ValueError:
            email = os.environ.get(MARQUISE_EMAIL_ENV_VAR)
            password = os.environ.get(MARQUISE_PASSWORD_ENV_VAR)
            if email and password:
                try:
                    self._auth.login(email=email, password=password)
                    # login already saves the session; validate again so
                    # the admin check isn't skipped
                    return self._auth.get_validated_session()
                except ValueError:
                    pass
            raise
