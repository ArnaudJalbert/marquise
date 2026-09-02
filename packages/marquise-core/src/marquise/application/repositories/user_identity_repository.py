"""Repository interface for user identity administration."""

from __future__ import annotations

from abc import ABC, abstractmethod

from marquise.domain.entities.user_identity import UserIdentity
from marquise.domain.value_objects.marquise_role import MarquiseRole


class UserIdentityRepository(ABC):
    """Administer Supabase user identities."""

    @abstractmethod
    async def invite(self, email: str) -> UserIdentity:
        """Invite a human user by email."""
        ...

    @abstractmethod
    async def find_by_email(self, email: str) -> UserIdentity | None:
        """Find one user by exact email."""
        ...

    @abstractmethod
    async def set_role(self, user_id: str, role: MarquiseRole | None) -> None:
        """Set or remove protected Marquise role metadata."""
        ...

    @abstractmethod
    async def delete(self, user_id: str) -> None:
        """Delete one user."""
        ...
