"""Repository contract for Bot account provisioning."""

from abc import ABC, abstractmethod

from marquise.domain.value_objects.bot_session import BotSession


class BotRepository(ABC):
    """Create Bot accounts and manage their protected metadata."""

    @abstractmethod
    async def identifier_exists(self, bot_id: str) -> bool:
        """Check whether any account already holds this Bot Identifier."""

    @abstractmethod
    async def create_anonymous(self) -> BotSession:
        """Create an anonymous account and return transient credentials."""

    @abstractmethod
    async def assign_editor(self, account_id: str, bot_id: str) -> None:
        """Assign the Editor role and immutable Bot Identifier."""

    @abstractmethod
    async def delete(self, account_id: str) -> None:
        """Delete an account created by an unsuccessful provisioning attempt."""
