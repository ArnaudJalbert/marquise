"""Tests for reusable FastAPI authorization dependencies."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from marquise import AuthenticationError, VerifyAccessTokenQuery
from marquise_api.app import create_app
from marquise_api.auth import (
    AuthenticatedCaller,
    require_administrator,
    require_authenticated,
    require_editor,
)


def _auth_client() -> tuple[TestClient, VerifyAccessTokenQuery]:
    query = create_autospec(VerifyAccessTokenQuery, instance=True)
    query.InputData = VerifyAccessTokenQuery.InputData

    async def verify(
        request: VerifyAccessTokenQuery.InputData,
    ) -> VerifyAccessTokenQuery.OutputData:
        if request.token == "invalid":
            raise AuthenticationError("invalid")
        role = request.token
        return VerifyAccessTokenQuery.OutputData(subject="user-id", role=role)

    query.execute.side_effect = verify
    app = create_app(verify_access_token_query=query)

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


def _bearer(role: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {role}"}


def test_dependencies_authorize_fixed_roles() -> None:
    """Authenticated, Editor, and Administrator dependencies enforce roles."""
    client, _ = _auth_client()

    response = client.get("/_test/authenticated", headers=_bearer("member"))
    assert response.json() == {"subject": "user-id", "role": "member"}
    assert client.get("/_test/editor", headers=_bearer("editor")).status_code == 200
    assert (
        client.get("/_test/editor", headers=_bearer("administrator")).status_code == 200
    )
    assert client.get("/_test/editor", headers=_bearer("member")).status_code == 403
    assert (
        client.get("/_test/administrator", headers=_bearer("editor")).status_code == 403
    )


@pytest.mark.parametrize(
    "headers",
    [None, {"Authorization": "Bad"}, _bearer("invalid")],
)
def test_dependencies_reject_missing_or_invalid_credentials(
    headers: dict[str, str] | None,
) -> None:
    """Missing, malformed, and unverifiable credentials receive 401."""
    client, _ = _auth_client()

    response = client.get("/_test/editor", headers=headers)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_dependency_reports_unconfigured_authentication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Protected future routes report unavailable configuration."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    app = create_app()

    @app.get("/_test/editor", dependencies=[Depends(require_editor)])
    async def editor() -> dict[str, str]:
        return {"status": "ok"}

    assert TestClient(app).get("/_test/editor").status_code == 503


def test_current_routes_remain_public_and_auth_endpoints_do_not_exist() -> None:
    """Auth readiness adds no protection or login routes to current API."""
    client, query = _auth_client()

    assert client.get("/health").status_code == 200
    assert client.post("/v1/auth/login").status_code == 404
    assert client.get("/v1/auth/me").status_code == 404
    query.execute.assert_not_awaited()
