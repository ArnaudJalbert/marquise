"""Repository interface for account administration."""

from __future__ import annotations

from abc import ABC, abstractmethod

from marquise.domain.entities.account import Account
from marquise.domain.value_objects.marquise_role import MarquiseRole


class AccountRepository(ABC):
    """Administer human accounts through the configured identity provider."""

    @abstractmethod
    async def invite(self, email: str) -> Account:
        """Invite a human account by email."""
        ...

    @abstractmethod
    async def find_by_email(self, email: str) -> Account | None:
        """Find one account by exact email."""
        ...

    @abstractmethod
    async def set_role(self, account_id: str, role: MarquiseRole) -> None:
        """Set protected Marquise role metadata."""
        ...
