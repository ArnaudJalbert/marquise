"""Public composition root for authentication use cases."""

from __future__ import annotations

import jwt

from marquise.application.queries.verify_access_token import VerifyAccessTokenQuery
from marquise.application.use_cases.authenticate_administrator import (
    AuthenticateAdministratorUseCase,
)
from marquise.application.use_cases.invite_auth_user import InviteAuthUserUseCase
from marquise.application.use_cases.set_auth_user_role import SetAuthUserRoleUseCase
from marquise.infrastructure.auth.supabase import (
    SupabaseAuthAdminGateway,
    SupabaseJwtGateway,
    SupabasePasswordAuthGateway,
    SupabaseSigningKeyProvider,
)
from marquise.interface_adapters.readers.user_identity_reader import (
    GatewayUserIdentityReader,
)
from marquise.interface_adapters.repositories.password_auth_repository import (
    GatewayPasswordAuthenticationRepository,
)
from marquise.interface_adapters.repositories.user_identity_repository import (
    GatewayUserIdentityRepository,
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
        self._identities = GatewayUserIdentityReader(gateway)

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
    def invite_auth_user_use_case(self) -> InviteAuthUserUseCase:
        """Configured human invitation use case."""
        return InviteAuthUserUseCase(self._auth_users)

    @property
    def set_auth_user_role_use_case(self) -> SetAuthUserRoleUseCase:
        """Configured human role-change use case."""
        return SetAuthUserRoleUseCase(self._auth_users)

    @property
    def _auth_users(self) -> GatewayUserIdentityRepository:
        if not self._service_role_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required")
        return GatewayUserIdentityRepository(
            SupabaseAuthAdminGateway(self._supabase_url, self._service_role_key)
        )
