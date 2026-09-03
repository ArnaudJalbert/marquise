"""Repository interface for password authentication."""

from __future__ import annotations

from abc import ABC, abstractmethod


class PasswordAuthenticationRepository(ABC):
    """Exchange human credentials for an access token."""

    @abstractmethod
    async def issue_access_token(self, email: str, password: str) -> str:
        """Authenticate credentials and return an access token."""
        ...
