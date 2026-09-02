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
    InvalidCredentialsError,
    IssuedSession,
    SigningKeyProvider,
    SupabaseJwtVerifier,
    TokenIssuanceError,
    TokenIssuer,
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


@pytest.fixture
def auth_client(verifier: SupabaseJwtVerifier) -> TestClient:
    """Provide test-only routes protected by each reusable dependency."""
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

    return TestClient(app)


def test_fastapi_dependencies_authorize_roles(
    auth_client: TestClient,
    private_key: rsa.RSAPrivateKey,
) -> None:
    """Role dependencies enforce authenticated, Editor, and Administrator access."""
    editor_token = _token(private_key, "editor")
    administrator_token = _token(private_key, "administrator")
    member_token = _token(private_key, "member")

    response = auth_client.get(
        "/_test/authenticated", headers={"Authorization": f"Bearer {member_token}"}
    )
    assert response.json() == {"subject": "user-1", "role": "member"}
    assert auth_client.get("/_test/editor").status_code == 401
    assert (
        auth_client.get("/_test/editor", headers={"Authorization": "Bad"}).status_code
        == 401
    )
    assert (
        auth_client.get(
            "/_test/editor", headers={"Authorization": "Bearer not-a-jwt"}
        ).status_code
        == 401
    )
    assert (
        auth_client.get(
            "/_test/editor", headers={"Authorization": f"Bearer {editor_token}"}
        ).status_code
        == 200
    )
    assert (
        auth_client.get(
            "/_test/editor", headers={"Authorization": f"Bearer {administrator_token}"}
        ).status_code
        == 200
    )
    assert (
        auth_client.get(
            "/_test/editor", headers={"Authorization": f"Bearer {member_token}"}
        ).status_code
        == 403
    )
    assert (
        auth_client.get(
            "/_test/administrator", headers={"Authorization": f"Bearer {editor_token}"}
        ).status_code
        == 403
    )


@pytest.mark.parametrize(
    ("role", "claims"),
    [
        ("editor", {"exp": (datetime.now(UTC) - timedelta(minutes=5)).timestamp()}),
        ("editor", {"iss": "https://other.supabase.co/auth/v1"}),
        ("editor", {"aud": "other"}),
        (None, {}),
    ],
)
def test_fastapi_boundary_rejects_invalid_claims(
    auth_client: TestClient,
    private_key: rsa.RSAPrivateKey,
    role: str | None,
    claims: dict,
) -> None:
    """Expired, wrong-scope, and roleless JWTs receive unauthorized responses."""
    token = _token(private_key, role, **claims)

    response = auth_client.get(
        "/_test/editor", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 401


def test_public_routes_ignore_missing_credentials() -> None:
    """Health stays public when authentication verifier is configured."""
    app = create_app(token_verifier=create_autospec(TokenVerifier, instance=True))

    assert TestClient(app).get("/health").status_code == 200


def test_me_route_returns_authenticated_caller(
    auth_client: TestClient, private_key: rsa.RSAPrivateKey
) -> None:
    """GET /v1/auth/me reports the caller's subject and role."""
    response = auth_client.get(
        "/v1/auth/me",
        headers={"Authorization": f"Bearer {_token(private_key, 'editor')}"},
    )

    assert response.status_code == 200
    assert response.json() == {"subject": "user-1", "role": "editor"}


@pytest.mark.parametrize(
    "headers",
    [None, {"Authorization": "Bearer not-a-jwt"}],
)
def test_me_route_rejects_missing_or_invalid_token(
    auth_client: TestClient, headers: dict[str, str] | None
) -> None:
    """Missing or malformed bearer tokens receive unauthorized responses."""
    response = auth_client.get("/v1/auth/me", headers=headers)

    assert response.status_code == 401


def test_login_route_returns_issued_session() -> None:
    """POST /v1/auth/login returns the session issued by the token issuer."""
    issuer = create_autospec(TokenIssuer, instance=True)
    issuer.issue.return_value = IssuedSession(
        access_token="access-token",
        refresh_token="refresh-token",
        expires_in=900,
    )
    app = create_app(
        token_verifier=create_autospec(TokenVerifier, instance=True),
        token_issuer=issuer,
    )

    response = TestClient(app).post(
        "/v1/auth/login",
        json={"email": "user@example.com", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "expires_in": 900,
        "token_type": "bearer",
    }
    issuer.issue.assert_awaited_once_with("user@example.com", "secret")


@pytest.mark.parametrize(
    ("side_effect", "expected_status"),
    [
        (InvalidCredentialsError("rejected"), 401),
        (TokenIssuanceError("provider down"), 503),
    ],
)
def test_login_route_maps_issuer_failures_to_status_codes(
    side_effect: Exception, expected_status: int
) -> None:
    """Rejected credentials and provider failures map to 401 and 503."""
    issuer = create_autospec(TokenIssuer, instance=True)
    issuer.issue.side_effect = side_effect
    app = create_app(
        token_verifier=create_autospec(TokenVerifier, instance=True),
        token_issuer=issuer,
    )

    response = TestClient(app).post(
        "/v1/auth/login",
        json={"email": "user@example.com", "password": "secret"},
    )

    assert response.status_code == expected_status


def test_login_route_reports_unconfigured_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Login returns 503 when no token issuer is configured."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    app = create_app(token_verifier=create_autospec(TokenVerifier, instance=True))

    response = TestClient(app).post(
        "/v1/auth/login",
        json={"email": "user@example.com", "password": "secret"},
    )

    assert response.status_code == 503


def test_login_route_validates_credentials_shape() -> None:
    """Malformed login bodies receive validation errors."""
    issuer = create_autospec(TokenIssuer, instance=True)
    app = create_app(
        token_verifier=create_autospec(TokenVerifier, instance=True),
        token_issuer=issuer,
    )

    response = TestClient(app).post(
        "/v1/auth/login",
        json={"email": "not-an-email", "password": ""},
    )

    assert response.status_code == 422
    issuer.issue.assert_not_awaited()
