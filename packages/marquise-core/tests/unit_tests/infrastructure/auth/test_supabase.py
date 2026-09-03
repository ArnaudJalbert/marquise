"""Tests for Supabase authentication gateways."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from io import BytesIO
from unittest.mock import MagicMock, create_autospec, patch
from urllib.error import HTTPError

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from marquise.infrastructure.auth import (
    SigningKeyProvider,
    SupabaseAuthAdminGateway,
    SupabaseJwtGateway,
    SupabasePasswordAuthGateway,
)
from marquise.interface_adapters.repositories.protocols.auth import AuthGatewayError

ISSUER = "https://project.supabase.co/auth/v1"
AUDIENCE = "authenticated"


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    """Provide key pair for deterministic signed tokens."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def jwt_gateway(private_key: rsa.RSAPrivateKey) -> SupabaseJwtGateway:
    """Provide JWT gateway with injected local signing key."""
    provider = create_autospec(SigningKeyProvider, instance=True)
    provider.get_signing_key.return_value = jwt.PyJWK.from_dict(
        jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), True)
    )
    return SupabaseJwtGateway(provider, ISSUER, AUDIENCE)


def _token(
    private_key: rsa.RSAPrivateKey,
    **claims: str | float,
) -> str:
    payload: dict = {
        "sub": "user-id",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": (datetime.now(UTC) + timedelta(minutes=5)).timestamp(),
        "app_metadata": {"marquise_role": "editor"},
    }
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256")


@pytest.mark.asyncio
async def test_jwt_gateway_verifies_signature_and_registered_claims(
    jwt_gateway: SupabaseJwtGateway,
    private_key: rsa.RSAPrivateKey,
) -> None:
    """Valid signed token returns trusted plain claims."""
    claims = await jwt_gateway.verify(_token(private_key))

    assert claims["sub"] == "user-id"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "claims",
    [
        {"exp": (datetime.now(UTC) - timedelta(minutes=1)).timestamp()},
        {"iss": "https://other.supabase.co/auth/v1"},
        {"aud": "other"},
    ],
)
async def test_jwt_gateway_rejects_invalid_registered_claims(
    jwt_gateway: SupabaseJwtGateway,
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, str | float],
) -> None:
    """Expired, wrong-issuer, and wrong-audience tokens fail verification."""
    with pytest.raises(AuthGatewayError):
        await jwt_gateway.verify(_token(private_key, **claims))


@pytest.mark.asyncio
async def test_jwt_gateway_rejects_bad_signature(
    jwt_gateway: SupabaseJwtGateway,
) -> None:
    """Token signed by untrusted key fails verification."""
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(AuthGatewayError):
        await jwt_gateway.verify(_token(wrong_key))


def _response(payload: dict) -> MagicMock:
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
    return response


@pytest.mark.asyncio
async def test_password_gateway_posts_password_grant() -> None:
    """Password gateway exchanges credentials without exposing service key."""
    gateway = SupabasePasswordAuthGateway(
        "https://project.supabase.co", "publishable-key"
    )
    with patch(
        "urllib.request.urlopen",
        return_value=_response({"access_token": "signed-token"}),
    ) as urlopen:
        token = await gateway.issue_access_token("admin@example.com", "secret")

    assert token == "signed-token"
    request = urlopen.call_args.args[0]
    assert request.full_url.endswith("/token?grant_type=password")
    assert json.loads(request.data) == {
        "email": "admin@example.com",
        "password": "secret",
    }


@pytest.mark.asyncio
async def test_admin_gateway_keeps_safe_http_error_detail() -> None:
    """Supabase error status and message remain available to CLI administrators."""
    gateway = SupabaseAuthAdminGateway("https://project.supabase.co", "service-key")
    error = HTTPError(
        "https://project.supabase.co/auth/v1/admin/invite",
        422,
        "Unprocessable Entity",
        None,
        BytesIO(b'{"msg":"User already registered"}'),
    )

    with patch("urllib.request.urlopen", side_effect=error):
        with pytest.raises(
            AuthGatewayError,
            match=r"Supabase Auth request failed \(422\): User already registered",
        ):
            await gateway.invite("user@example.com")


@pytest.mark.asyncio
async def test_admin_gateway_invites_and_updates_protected_metadata() -> None:
    """Admin gateway uses invite endpoint and protected application metadata."""
    gateway = SupabaseAuthAdminGateway("https://project.supabase.co", "service-key")
    responses = [
        _response({"id": "user-id", "email": "user@example.com"}),
        _response({}),
        _response({}),
    ]
    with patch("urllib.request.urlopen", side_effect=responses) as urlopen:
        user = await gateway.invite("user@example.com")
        await gateway.set_role("user-id", "editor")
        await gateway.set_role("user-id", None)

    assert user["id"] == "user-id"
    invite_request = urlopen.call_args_list[0].args[0]
    role_request = urlopen.call_args_list[1].args[0]
    clear_request = urlopen.call_args_list[2].args[0]
    assert invite_request.full_url == "https://project.supabase.co/auth/v1/invite"
    assert json.loads(invite_request.data) == {"email": "user@example.com"}
    assert (
        role_request.full_url
        == "https://project.supabase.co/auth/v1/admin/users/user-id"
    )
    assert json.loads(role_request.data) == {
        "app_metadata": {"marquise_role": "editor"}
    }
    assert json.loads(clear_request.data) == {"app_metadata": {"marquise_role": None}}
    assert role_request.headers["Authorization"] == "Bearer service-key"
