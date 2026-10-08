"""Map provider account data to transient Bot sessions."""

from marquise.application.exceptions.auth import AuthAdministrationError
from marquise.application.repositories.bot_repository import BotRepository
from marquise.domain.value_objects.bot_session import BotSession
from marquise.interface_adapters.exceptions.auth import AuthGatewayError
from marquise.interface_adapters.repositories.protocols.auth import BotAuthGateway


class GatewayBotRepository(BotRepository):
    """Adapt an injected Auth provider to Bot provisioning operations."""

    def __init__(self, gateway: BotAuthGateway) -> None:
        """Initialize with the external Auth gateway."""
        self._gateway = gateway

    async def identifier_exists(self, bot_id: str) -> bool:
        """Check all accounts without filtering by Marquise role."""
        try:
            return await self._gateway.identifier_exists(bot_id)
        except AuthGatewayError as exc:
            raise AuthAdministrationError("Unable to check Bot Identifier") from exc

    async def create_anonymous(self) -> BotSession:
        """Create an anonymous account and validate its transient credentials."""
        try:
            data = await self._gateway.create_anonymous()
        except AuthGatewayError as exc:
            raise AuthAdministrationError(
                "Unable to create anonymous Bot account"
            ) from exc
        user = data.get("user")
        account_id = user.get("id") if isinstance(user, dict) else None
        token = data.get("refresh_token")
        if not isinstance(account_id, str) or not account_id:
            raise AuthAdministrationError("Bot response has no account ID")
        if not isinstance(token, str) or not token:
            await self.delete(account_id)
            raise AuthAdministrationError("Bot response has no refresh token")
        return BotSession(account_id=account_id, refresh_token=token)

    async def assign_editor(self, account_id: str, bot_id: str) -> None:
        """Assign protected role and identifier metadata."""
        try:
            await self._gateway.assign_editor(account_id, bot_id)
        except AuthGatewayError as exc:
            raise AuthAdministrationError("Unable to assign Bot metadata") from exc

    async def delete(self, account_id: str) -> None:
        """Delete the account after an unsuccessful provisioning attempt."""
        try:
            await self._gateway.delete(account_id)
        except AuthGatewayError as exc:
            raise AuthAdministrationError(
                f"Unable to delete Bot account {account_id}"
            ) from exc
