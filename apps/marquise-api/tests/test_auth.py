"""Tests for reusable FastAPI authorization dependencies."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from marquise import (
    AuthenticationError,
    AuthenticationServiceUnavailableError,
    MarquiseFactory,
    VerifyAccessTokenQuery,
)
from marquise_api.app import create_app
from marquise_api.auth import (
    AuthenticatedCaller,
    require_administrator,
    require_authenticated,
    require_editor,
)


def _auth_client(
    *,
    configured: bool = True,
) -> tuple[TestClient, VerifyAccessTokenQuery]:
    query = create_autospec(VerifyAccessTokenQuery, instance=True)
    query.InputData = VerifyAccessTokenQuery.InputData

    async def verify(
        request: VerifyAccessTokenQuery.InputData,
    ) -> VerifyAccessTokenQuery.OutputData:
        if request.token == "unavailable":
            raise AuthenticationServiceUnavailableError("JWKS unavailable")
        if request.token in {
            "invalid-signature",
            "expired",
            "wrong-issuer",
            "wrong-audience",
            "missing-role",
        }:
            raise AuthenticationError("invalid")
        return VerifyAccessTokenQuery.OutputData(
            subject="user-id",
            role=request.token,
        )

    query.execute.side_effect = verify
    factory = create_autospec(MarquiseFactory, instance=True)
    factory.verify_access_token_query = query if configured else None
    app = create_app(factory=factory)

    @app.get("/_test/authenticated")
    async def authenticated(
        caller: AuthenticatedCaller = Depends(require_authenticated),
    ) -> dict[str, str]:
        return {"subject": caller.subject, "role": caller.role}

    @app.get("/_test/editor", dependencies=[Depends(require_editor)])
    async def editor() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/_test/administrator",
        dependencies=[Depends(require_administrator)],
    )
    async def administrator() -> dict[str, str]:
        return {"status": "ok"}

    return TestClient(app), query


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _assert_error_envelope(
    response_status: int,
    response_json: dict,
    *,
    expected_status: int,
    expected_code: str,
    expected_detail: str,
) -> None:
    assert response_status == expected_status
    assert response_json["error_code"] == expected_code
    assert response_json["detail"] == expected_detail
    assert isinstance(response_json["request_id"], str)


def test_dependencies_authorize_fixed_roles() -> None:
    """Authenticated, Editor, and Administrator dependencies enforce roles."""
    client, _ = _auth_client()

    response = client.get(
        "/_test/authenticated",
        headers=_bearer("member"),
    )
    assert response.json() == {"subject": "user-id", "role": "member"}
    assert (
        client.get(
            "/_test/editor",
            headers=_bearer("editor"),
        ).status_code
        == 200
    )
    assert (
        client.get(
            "/_test/editor",
            headers=_bearer("administrator"),
        ).status_code
        == 200
    )

    forbidden = client.get(
        "/_test/editor",
        headers=_bearer("member"),
    )
    _assert_error_envelope(
        forbidden.status_code,
        forbidden.json(),
        expected_status=403,
        expected_code="authorization_error",
        expected_detail="Editor role required",
    )
    assert (
        client.get(
            "/_test/administrator",
            headers=_bearer("administrator"),
        ).status_code
        == 200
    )


@pytest.mark.parametrize(
    "headers",
    [None, {"Authorization": "Bad"}],
)
def test_dependencies_reject_missing_or_malformed_credentials(
    headers: dict[str, str] | None,
) -> None:
    """Missing and malformed credentials receive a standard 401."""
    client, _ = _auth_client()

    response = client.get("/_test/editor", headers=headers)

    _assert_error_envelope(
        response.status_code,
        response.json(),
        expected_status=401,
        expected_code="authentication_error",
        expected_detail="Missing bearer token",
    )
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "token",
    [
        "invalid-signature",
        "expired",
        "wrong-issuer",
        "wrong-audience",
        "missing-role",
    ],
)
def test_dependencies_reject_each_invalid_token_boundary(token: str) -> None:
    """Invalid signature, claims, expiry, and role all receive a standard 401."""
    client, _ = _auth_client()

    response = client.get("/_test/editor", headers=_bearer(token))

    _assert_error_envelope(
        response.status_code,
        response.json(),
        expected_status=401,
        expected_code="authentication_error",
        expected_detail="Invalid bearer token",
    )
    assert response.headers["www-authenticate"] == "Bearer"


def test_dependency_reports_signing_key_outage_as_unavailable() -> None:
    """A JWKS outage receives 503 instead of invalid-token 401."""
    client, _ = _auth_client()

    response = client.get(
        "/_test/editor",
        headers=_bearer("unavailable"),
    )

    _assert_error_envelope(
        response.status_code,
        response.json(),
        expected_status=503,
        expected_code="service_unavailable",
        expected_detail="Authentication service is unavailable",
    )


def test_dependency_reports_unconfigured_authentication() -> None:
    """Protected future routes report unavailable configuration."""
    client, _ = _auth_client(configured=False)

    response = client.get(
        "/_test/editor",
        headers=_bearer("editor"),
    )

    _assert_error_envelope(
        response.status_code,
        response.json(),
        expected_status=503,
        expected_code="service_unavailable",
        expected_detail="Authentication is not configured",
    )


def test_current_routes_remain_public_and_auth_endpoints_do_not_exist() -> None:
    """Auth readiness adds no protection or login routes to current API."""
    client, query = _auth_client()

    assert client.get("/health").status_code == 200
    assert client.post("/v1/auth/login").status_code == 404
    assert client.get("/v1/auth/me").status_code == 404
    query.execute.assert_not_awaited()
