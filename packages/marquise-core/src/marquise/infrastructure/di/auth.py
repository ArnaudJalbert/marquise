"""Authentication dependency wiring."""

from __future__ import annotations

import jwt

from marquise.application.queries.verify_access_token import VerifyAccessTokenQuery
from marquise.application.use_cases.auth import (
    AuthenticateAdministratorUseCase,
    InviteAccountUseCase,
    SetAccountRoleUseCase,
)
from marquise.infrastructure.auth.gotrue import GoTrueAuthGateway
from marquise.infrastructure.auth.jwks import JwksSigningKeyProvider
from marquise.interface_adapters.readers.account_identity_reader import (
    GatewayAccountIdentityReader,
)
from marquise.interface_adapters.readers.jwt_access_token import (
    JwtAccessTokenGateway,
)
from marquise.interface_adapters.repositories.account_repository import (
    GatewayAccountRepository,
)
from marquise.interface_adapters.repositories.password_auth_repository import (
    GatewayPasswordAuthenticationRepository,
)


def _require(value: str, environment_name: str) -> str:
    """Return configured value or report the missing environment variable."""
    if not value:
        raise RuntimeError(f"{environment_name} is required")
    return value


def _identity_reader(supabase_url: str) -> GatewayAccountIdentityReader:
    """Build the shared verified-identity reader."""
    issuer = f"{_require(supabase_url, 'SUPABASE_URL').rstrip('/')}/auth/v1"
    gateway = JwtAccessTokenGateway(
        signing_keys=JwksSigningKeyProvider(
            jwt.PyJWKClient(f"{issuer}/.well-known/jwks.json")
        ),
        issuer=issuer,
    )
    return GatewayAccountIdentityReader(gateway)


def _gotrue_gateway(
    supabase_url: str,
    publishable_key: str = "",
    service_role_key: str = "",
) -> GoTrueAuthGateway:
    """Build the provider gateway used by local administration workflows."""
    auth_url = f"{_require(supabase_url, 'SUPABASE_URL').rstrip('/')}/auth/v1"
    return GoTrueAuthGateway(
        auth_url=auth_url,
        publishable_key=publishable_key,
        service_role_key=service_role_key,
    )


def build_verify_access_token_query(supabase_url: str) -> VerifyAccessTokenQuery:
    """Build access-token verification without database dependencies."""
    return VerifyAccessTokenQuery(_identity_reader(supabase_url))


def build_authenticate_administrator_use_case(
    supabase_url: str,
    publishable_key: str,
) -> AuthenticateAdministratorUseCase:
    """Build Administrator authentication without database dependencies."""
    gateway = _gotrue_gateway(
        supabase_url,
        _require(publishable_key, "SUPABASE_PUBLISHABLE_KEY"),
    )
    return AuthenticateAdministratorUseCase(
        GatewayPasswordAuthenticationRepository(gateway),
        _identity_reader(supabase_url),
    )


def build_invite_account_use_case(
    supabase_url: str,
    publishable_key: str,
    service_role_key: str,
) -> InviteAccountUseCase:
    """Build the authorized human-account invitation workflow."""
    gateway = _gotrue_gateway(
        supabase_url,
        _require(publishable_key, "SUPABASE_PUBLISHABLE_KEY"),
        _require(service_role_key, "SUPABASE_SERVICE_ROLE_KEY"),
    )
    return InviteAccountUseCase(
        GatewayAccountRepository(gateway),
        AuthenticateAdministratorUseCase(
            GatewayPasswordAuthenticationRepository(gateway),
            _identity_reader(supabase_url),
        ),
    )


def build_set_account_role_use_case(
    supabase_url: str,
    publishable_key: str,
    service_role_key: str,
) -> SetAccountRoleUseCase:
    """Build the authorized account role-change workflow."""
    gateway = _gotrue_gateway(
        supabase_url,
        _require(publishable_key, "SUPABASE_PUBLISHABLE_KEY"),
        _require(service_role_key, "SUPABASE_SERVICE_ROLE_KEY"),
    )
    return SetAccountRoleUseCase(
        GatewayAccountRepository(gateway),
        AuthenticateAdministratorUseCase(
            GatewayPasswordAuthenticationRepository(gateway),
            _identity_reader(supabase_url),
        ),
    )
