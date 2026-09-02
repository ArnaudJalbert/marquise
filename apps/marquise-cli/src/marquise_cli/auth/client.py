"""Supabase Auth Admin API client (stdlib HTTP)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class AuthError(RuntimeError):
    """Raised when the Supabase Auth Admin API returns an error."""


@dataclass(frozen=True, slots=True)
class AuthUser:
    """User record returned by Supabase Auth."""

    id: str
    email: str | None
    created_at: str | None


class AuthClient:
    """Minimal Supabase GoTrue admin client."""

    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        self._base_url = f"{supabase_url}/auth/v1/admin"
        self._service_role_key = service_role_key

    def create_user(
        self,
        *,
        email: str,
        password: str,
        email_confirm: bool = True,
    ) -> AuthUser:
        payload = self._request(
            "POST",
            "users",
            {
                "email": email,
                "password": password,
                "email_confirm": email_confirm,
            },
        )
        return _parse_user(payload)

    def update_user(
        self,
        user_id: str,
        *,
        email: str | None = None,
        password: str | None = None,
    ) -> AuthUser:
        body: dict[str, Any] = {}
        if email is not None:
            body["email"] = email
        if password is not None:
            body["password"] = password
        if not body:
            raise ValueError("At least one of email or password must be provided")
        payload = self._request("PUT", f"users/{user_id}", body)
        return _parse_user(payload)

    def delete_user(self, user_id: str) -> None:
        self._request("DELETE", f"users/{user_id}")

    def get_user(self, user_id: str) -> AuthUser:
        payload = self._request("GET", f"users/{user_id}")
        return _parse_user(payload)

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/{path}"
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(  # noqa: S310
            url,
            data=data,
            method=method,
            headers={
                "apikey": self._service_role_key,
                "Authorization": f"Bearer {self._service_role_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request) as response:  # noqa: S310
                raw = response.read().decode()
        except urllib.error.HTTPError as error:
            detail = error.read().decode()
            message = detail
            try:
                parsed = json.loads(detail)
                message = parsed.get("msg") or parsed.get("message") or detail
            except json.JSONDecodeError:
                pass
            raise AuthError(f"Auth API {method} {path} failed: {message}") from error
        if not raw:
            return {}
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise AuthError(f"Unexpected Auth API response: {raw!r}")
        return parsed


def _parse_user(payload: dict[str, Any]) -> AuthUser:
    user = payload.get("user", payload)
    if not isinstance(user, dict):
        raise AuthError(f"Unexpected user payload: {payload!r}")
    user_id = user.get("id")
    if not user_id:
        raise AuthError(f"Auth user payload missing id: {payload!r}")
    email = user.get("email")
    created_at = user.get("created_at")
    return AuthUser(
        id=str(user_id),
        email=str(email) if email else None,
        created_at=str(created_at) if created_at else None,
    )
