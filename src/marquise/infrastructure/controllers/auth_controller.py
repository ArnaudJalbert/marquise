"""Controller for authentication operations."""

from __future__ import annotations

from typing import Optional

from marquise.interface_adapters.repositories.protocols.auth import (
    AuthService,
    AuthSession,
)


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

    def status(self) -> Optional[AuthSession]:
        return self._auth.get_session_status()

    def validate_admin(self) -> AuthSession:
        return self._auth.get_validated_session()
