"""GoTrue HTTP authentication gateway used by Supabase Auth."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request

from marquise.interface_adapters.exceptions.auth import (
    AuthGatewayError,
    AuthGatewayUnavailableError,
)


class GoTrueAuthGateway:
    """Authenticate and administer accounts through a GoTrue-compatible API."""

    def __init__(
        self,
        auth_url: str,
        publishable_key: str = "",
        service_role_key: str = "",
    ) -> None:
        """Initialize the provider endpoint and credentials."""
        self._auth_url = auth_url.rstrip("/")
        self._publishable_key = publishable_key
        self._service_role_key = service_role_key

    async def issue_access_token(self, email: str, password: str) -> str:
        """Authenticate password credentials and return an access token."""
        if not self._publishable_key:
            raise RuntimeError("SUPABASE_PUBLISHABLE_KEY is required")
        payload = await self._request(
            "POST",
            "token?grant_type=password",
            self._publishable_key,
            {"email": email, "password": password},
        )
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise AuthGatewayError("Authentication response has no access token")
        return token

    async def invite(self, email: str) -> dict:
        """Send an invitation and return the invited account data."""
        if not self._service_role_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required")
        payload = await self._request(
            "POST",
            "invite",
            self._service_role_key,
            {"email": email},
            authorize=True,
        )
        account = payload.get("user", payload)
        if not isinstance(account, dict):
            raise AuthGatewayError("Invitation returned no account")
        return account

    async def find_by_email(self, email: str) -> dict | None:
        """Find one account by exact case-insensitive email."""
        if not self._service_role_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required")
        query = urllib.parse.urlencode({"filter": email})
        payload = await self._request(
            "GET",
            f"admin/users?{query}",
            self._service_role_key,
            authorize=True,
        )
        accounts = payload.get("users")
        if not isinstance(accounts, list):
            raise AuthGatewayError("Account search returned invalid data")
        normalized = email.casefold()
        return next(
            (
                account
                for account in accounts
                if isinstance(account, dict)
                and isinstance(account.get("email"), str)
                and account["email"].casefold() == normalized
            ),
            None,
        )

    async def set_role(self, user_id: str, role: str) -> None:
        """Set protected application role metadata."""
        if not self._service_role_key:
            raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is required")
        await self._request(
            "PUT",
            f"admin/users/{user_id}",
            self._service_role_key,
            {"app_metadata": {"marquise_role": role}},
            authorize=True,
        )

    async def _request(
        self,
        method: str,
        path: str,
        api_key: str,
        body: dict | None = None,
        *,
        authorize: bool = False,
    ) -> dict:
        """Execute one blocking provider request outside the event loop."""
        return await asyncio.to_thread(
            self._request_sync,
            method,
            path,
            api_key,
            body,
            authorize=authorize,
        )

    def _request_sync(
        self,
        method: str,
        path: str,
        api_key: str,
        body: dict | None,
        *,
        authorize: bool,
    ) -> dict:
        """Execute one JSON request through the standard-library HTTP client."""
        headers = {
            "apikey": api_key,
            "Content-Type": "application/json",
        }
        if authorize:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(  # noqa: S310
            f"{self._auth_url}/{path}",
            data=None if body is None else json.dumps(body).encode(),
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
                raw = response.read().decode()
        except urllib.error.HTTPError as exc:
            detail = str(exc.reason)
            try:
                payload = json.loads(exc.read().decode())
                if isinstance(payload, dict):
                    message = (
                        payload.get("msg")
                        or payload.get("message")
                        or payload.get("error_description")
                        or payload.get("error")
                    )
                    if isinstance(message, str) and message:
                        detail = message
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
            raise AuthGatewayError(
                f"Authentication request failed ({exc.code}): {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AuthGatewayUnavailableError(
                f"Authentication service is unavailable: {exc.reason}"
            ) from exc

        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AuthGatewayError(
                "Authentication provider returned invalid JSON"
            ) from exc
        if not isinstance(payload, dict):
            raise AuthGatewayError("Authentication provider returned invalid data")
        return payload
