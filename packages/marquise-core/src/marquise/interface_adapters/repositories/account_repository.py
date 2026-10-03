"""Gateway-backed account repository."""

from __future__ import annotations

from marquise.application.exceptions.auth import AuthAdministrationError
from marquise.application.repositories.account_repository import AccountRepository
from marquise.domain.entities.account import Account
from marquise.domain.value_objects.marquise_role import MarquiseRole
from marquise.interface_adapters.exceptions.auth import AuthGatewayError
from marquise.interface_adapters.repositories.protocols.auth import AuthAdminGateway


class GatewayAccountRepository(AccountRepository):
    """Map identity-provider gateway data to accounts."""

    def __init__(self, gateway: AuthAdminGateway) -> None:
        """Initialize with Auth Admin gateway."""
        self._gateway = gateway

    async def invite(self, email: str) -> Account:
        """Invite an account and map returned data."""
        try:
            return self._to_account(await self._gateway.invite(email))
        except (AuthGatewayError, ValueError) as exc:
            raise AuthAdministrationError(f"Unable to invite account: {exc}") from exc

    async def find_by_email(self, email: str) -> Account | None:
        """Find an account by exact email."""
        try:
            data = await self._gateway.find_by_email(email)
            return self._to_account(data) if data is not None else None
        except (AuthGatewayError, ValueError) as exc:
            raise AuthAdministrationError(f"Unable to find account: {exc}") from exc

    async def set_role(self, account_id: str, role: MarquiseRole) -> None:
        """Set protected Marquise role metadata."""
        try:
            await self._gateway.set_role(account_id, role.value)
        except AuthGatewayError as exc:
            raise AuthAdministrationError(
                f"Unable to update account role: {exc}"
            ) from exc

    @staticmethod
    def _to_account(data: dict) -> Account:
        """Map plain gateway user data to domain entity."""
        account_id = data.get("id")
        email = data.get("email")
        metadata = data.get("app_metadata")
        role_value = (
            metadata.get("marquise_role") if isinstance(metadata, dict) else None
        )
        if not isinstance(account_id, str) or not isinstance(email, str):
            raise ValueError("invalid account identity")
        role = MarquiseRole(role_value) if role_value is not None else None
        return Account(id=account_id, email=email, role=role)
