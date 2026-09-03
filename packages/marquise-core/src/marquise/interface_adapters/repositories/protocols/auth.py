"""Gateway interfaces for Supabase authentication."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AuthGatewayError(RuntimeError):
    """External authentication provider request failed."""


class AuthGatewayUnavailableError(AuthGatewayError):
    """External authentication provider is temporarily unavailable."""


class AccessTokenGateway(ABC):
    """Verify encoded access tokens and return plain claims."""

    @abstractmethod
    async def verify(self, token: str) -> dict:
        """Verify token and return claims."""
        ...


class PasswordAuthGateway(ABC):
    """Exchange password credentials for access tokens."""

    @abstractmethod
    async def issue_access_token(self, email: str, password: str) -> str:
        """Authenticate credentials and return access token."""
        ...


class AuthAdminGateway(ABC):
    """Administer users through trusted Supabase credentials."""

    @abstractmethod
    async def invite(self, email: str) -> dict:
        """Invite user and return plain user data."""
        ...

    @abstractmethod
    async def find_by_email(self, email: str) -> dict | None:
        """Find user by exact email."""
        ...

    @abstractmethod
    async def set_role(self, user_id: str, role: str) -> None:
        """Set protected role metadata."""
        ...
