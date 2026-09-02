"""Tests for injected Supabase JWT authentication dependencies."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import create_autospec

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends
from fastapi.testclient import TestClient

from marquise_api.app import create_app
from marquise_api.auth import (
    AuthenticatedCaller,
    SigningKeyProvider,
    SupabaseJwtVerifier,
    TokenVerificationError,
    TokenVerifier,
    require_administrator,
    require_authenticated,
    require_editor,
)

ISSUER = "https://project.supabase.co/auth/v1"
AUDIENCE = "authenticated"


@pytest.fixture
def private_key() -> rsa.RSAPrivateKey:
    """Provide a key pair for signed test tokens."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def verifier(private_key: rsa.RSAPrivateKey) -> SupabaseJwtVerifier:
    """Provide a verifier with an injected local signing key."""
    provider = create_autospec(SigningKeyProvider, instance=True)
    provider.get_signing_key.return_value = jwt.PyJWK.from_dict(
        jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key(), True)
    )
    return SupabaseJwtVerifier(
        signing_key_provider=provider,
        issuer=ISSUER,
        audience=AUDIENCE,
    )


def _token(
    private_key: rsa.RSAPrivateKey,
    role: str | None = "editor",
    **claims: str | float,
) -> str:
    payload: dict = {
        "sub": "user-1",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "exp": (datetime.now(UTC) + timedelta(minutes=5)).timestamp(),
    }
    if role is not None:
        payload["app_metadata"] = {"marquise_role": role}
    payload.update(claims)
    return jwt.encode(payload, private_key, algorithm="RS256")


@pytest.mark.parametrize(
    ("claims", "expected_message"),
    [
        ({"exp": (datetime.now(UTC) - timedelta(minutes=5)).timestamp()}, "expired"),
        ({"iss": "https://other.supabase.co/auth/v1"}, "issuer"),
        ({"aud": "other"}, "audience"),
    ],
)
def test_verifier_rejects_invalid_registered_claims(
    verifier: SupabaseJwtVerifier,
    private_key: rsa.RSAPrivateKey,
    claims: dict[str, str | float],
    expected_message: str,
) -> None:
    """Invalid expiry, issuer, or audience cannot authenticate a caller."""
    with pytest.raises(TokenVerificationError, match=expected_message):
        verifier.verify(_token(private_key, **claims))


def test_verifier_rejects_bad_signatures_and_missing_roles(
    verifier: SupabaseJwtVerifier,
    private_key: rsa.RSAPrivateKey,
) -> None:
    """Malformed, incorrectly signed, and roleless JWTs cannot authenticate."""
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    with pytest.raises(TokenVerificationError):
        verifier.verify("not-a-jwt")
    with pytest.raises(TokenVerificationError):
        verifier.verify(_token(wrong_key))
    with pytest.raises(TokenVerificationError, match="role"):
        verifier.verify(_token(private_key, role=None))
    with pytest.raises(TokenVerificationError, match="role"):
        verifier.verify(_token(private_key, role="owner"))


def test_fastapi_dependencies_authorize_roles(
    verifier: SupabaseJwtVerifier,
    private_key: rsa.RSAPrivateKey,
) -> None:
    """Editor dependency accepts Editors and Administrators but not Members."""
    app = create_app(token_verifier=verifier)

    @app.get("/_test/authenticated")
    def authenticated(
        caller: AuthenticatedCaller = Depends(require_authenticated),
    ) -> dict[str, str]:
        return {"subject": caller.subject, "role": caller.role}

    @app.get("/_test/editor")
    def editor(caller: AuthenticatedCaller = Depends(require_editor)) -> dict[str, str]:
        return {"subject": caller.subject, "role": caller.role}

    @app.get("/_test/administrator")
    def administrator(
        caller: AuthenticatedCaller = Depends(require_administrator),
    ) -> dict[str, str]:
        return {"subject": caller.subject, "role": caller.role}

    client = TestClient(app)
    editor_token = _token(private_key, "editor")
    administrator_token = _token(private_key, "administrator")
    member_token = _token(private_key, "member")

    response = client.get(
        "/_test/authenticated", headers={"Authorization": f"Bearer {member_token}"}
    )
    assert response.json() == {"subject": "user-1", "role": "member"}
    assert client.get("/_test/editor").status_code == 401
    malformed = client.get("/_test/editor", headers={"Authorization": "Bad"})
    invalid = client.get("/_test/editor", headers={"Authorization": "Bearer not-a-jwt"})
    assert malformed.status_code == 401
    assert invalid.status_code == 401
    assert (
        client.get(
            "/_test/editor", headers={"Authorization": f"Bearer {editor_token}"}
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/_test/editor", headers={"Authorization": f"Bearer {administrator_token}"}
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/_test/editor", headers={"Authorization": f"Bearer {member_token}"}
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/_test/administrator", headers={"Authorization": f"Bearer {editor_token}"}
        ).status_code
        == 403
    )


def test_public_routes_ignore_missing_credentials() -> None:
    """Health stays public when authentication verifier is configured."""
    app = create_app(token_verifier=create_autospec(TokenVerifier, instance=True))

    assert TestClient(app).get("/health").status_code == 200
