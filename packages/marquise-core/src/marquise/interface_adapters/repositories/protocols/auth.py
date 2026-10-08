"""Gateway protocols for external authentication providers."""

from __future__ import annotations

from typing import Protocol


class SigningKeyProvider(Protocol):
    """Verify an encoded token through a trusted signing-key provider."""

    def verify(self, token: str, issuer: str, audience: str) -> dict:
        """Return plain verified claims."""
        ...


class AccessTokenGateway(Protocol):
    """Verify encoded access tokens and return plain claims."""

    async def verify(self, token: str) -> dict:
        """Verify token and return claims."""
        ...


class PasswordAuthGateway(Protocol):
    """Exchange password credentials for access tokens."""

    async def issue_access_token(self, email: str, password: str) -> str:
        """Authenticate credentials and return access token."""
        ...


class AuthAdminGateway(Protocol):
    """Administer accounts through trusted provider credentials."""

    async def invite(self, email: str) -> dict:
        """Invite user and return plain user data."""
        ...

    async def find_by_email(self, email: str) -> dict | None:
        """Find user by exact email."""
        ...

    async def set_role(self, user_id: str, role: str) -> None:
        """Set protected role metadata."""
        ...


class BotAuthGateway(Protocol):
    """Provision anonymous accounts through an external Auth provider."""

    async def identifier_exists(self, bot_id: str) -> bool:
        """Search all accounts for an exact Bot Identifier."""
        ...

    async def create_anonymous(self) -> dict:
        """Return the new account and transient session credentials."""
        ...

    async def assign_editor(self, account_id: str, bot_id: str) -> None:
        """Set protected Editor and Bot Identifier metadata."""
        ...

    async def delete(self, account_id: str) -> None:
        """Delete a newly created account after setup fails."""
        ...
