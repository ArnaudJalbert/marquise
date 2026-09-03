"""Public composition root for authentication use cases."""

from __future__ import annotations

import jwt

from marquise.application.queries.verify_access_token import VerifyAccessTokenQuery
from marquise.application.use_cases.authenticate_administrator import (
    AuthenticateAdministratorUseCase,
)
from marquise.application.use_cases.invite_account import InviteAccountUseCase
from marquise.application.use_cases.set_account_role import SetAccountRoleUseCase
from marquise.infrastructure.auth.supabase import (
    SupabaseAuthAdminGateway,
    SupabaseJwtGateway,
    SupabasePasswordAuthGateway,
    SupabaseSigningKeyProvider,
)
from marquise.interface_adapters.readers.account_identity_reader import (
    GatewayAccountIdentityReader,
)
from marquise.interface_adapters.repositories.account_repository import (
    GatewayAccountRepository,
)
from marquise.interface_adapters.repositories.password_auth_repository import (
    GatewayPasswordAuthenticationRepository,
)


class AuthFactory:
    """Build configured auth use cases without requiring database access."""

    def __init__(
        self,
        supabase_url: str,
        publishable_key: str | None = None,
        service_role_key: str | None = None,
    ) -> None:
        """Configure Supabase authentication collaborators."""
        url = supabase_url.rstrip("/")
        if not url:
            raise ValueError("supabase_url must not be empty")
        self._supabase_url = url
        self._publishable_key = publishable_key
        self._service_role_key = service_role_key

        issuer = f"{url}/auth/v1"
        gateway = SupabaseJwtGateway(
            signing_keys=SupabaseSigningKeyProvider(
                jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json")
            ),
            issuer=issuer,
        )
        self._identities = GatewayAccountIdentityReader(gateway)

    @property
    def verify_access_token_query(self) -> VerifyAccessTokenQuery:
        """Configured access-token verification query."""
        return VerifyAccessTokenQuery(self._identities)

    @property
    def authenticate_administrator_use_case(
        self,
    ) -> AuthenticateAdministratorUseCase:
        """Configured Administrator password-authentication use case."""
        if not self._publishable_key:
            raise RuntimeError("SUPABASE_PUBLISHABLE_KEY is required")
        passwords = GatewayPasswordAuthenticationRepository(
            SupabasePasswordAuthGateway(self._supabase_url, self._publishable_key)
        )
        return AuthenticateAdministratorUseCase(passwords, self._identities)

    @property
    def invite_account_use_case(self) -> InviteAccountUseCase:
        """Configured human invitation use case."""
        return InviteAccountUseCase(self._accounts)

    @property
    def set_account_role_use_case(self) -> SetAccountRoleUseCase:
        """Configured human role-change use case."""
        return SetAccountRoleUseCase(self._accounts)

    @property
    def _accounts(self) -> GatewayAccountRepository:
        if not self._service_role_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required")
        return GatewayAccountRepository(
            SupabaseAuthAdminGateway(self._supabase_url, self._service_role_key)
        )
