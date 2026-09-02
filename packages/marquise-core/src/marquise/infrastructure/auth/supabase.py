"""Supabase HTTP and JWT authentication gateways."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod

import jwt

from marquise.interface_adapters.repositories.protocols.auth import (
    AccessTokenGateway,
    AuthAdminGateway,
    AuthGatewayError,
    PasswordAuthGateway,
)


class SigningKeyProvider(ABC):
    """Resolve a trusted signing key for an encoded JWT."""

    @abstractmethod
    def get_signing_key(self, token: str) -> jwt.PyJWK:
        """Return key matching token header."""
        ...


class SupabaseSigningKeyProvider(SigningKeyProvider):
    """Resolve signing keys through Supabase JWKS."""

    def __init__(self, client: jwt.PyJWKClient) -> None:
        """Initialize with JWKS client."""
        self._client = client

    def get_signing_key(self, token: str) -> jwt.PyJWK:
        """Return trusted signing key selected by token key ID."""
        return self._client.get_signing_key_from_jwt(token)


class SupabaseJwtGateway(AccessTokenGateway):
    """Verify Supabase access JWT signature and registered claims."""

    def __init__(
        self,
        signing_keys: SigningKeyProvider,
        issuer: str,
        audience: str = "authenticated",
    ) -> None:
        """Initialize trusted key provider and expected claims."""
        self._signing_keys = signing_keys
        self._issuer = issuer
        self._audience = audience

    async def verify(self, token: str) -> dict:
        """Verify token without blocking async delivery workers."""
        return await asyncio.to_thread(self._verify, token)

    def _verify(self, token: str) -> dict:
        try:
            key = self._signing_keys.get_signing_key(token)
            algorithm = key.algorithm_name
            if algorithm not in {"RS256", "ES256"}:
                raise AuthGatewayError("Unsupported JWT signing algorithm")
            claims = jwt.decode(
                token,
                key=key,
                algorithms=[algorithm],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
            if not isinstance(claims, dict):
                raise AuthGatewayError("Invalid JWT claims")
            return claims
        except (jwt.PyJWTError, ValueError) as exc:
            raise AuthGatewayError("Access token verification failed") from exc


class _SupabaseHttpGateway:
    """Shared stdlib JSON transport for trusted Supabase Auth calls."""

    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key

    async def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        *,
        authorize: bool = False,
    ) -> dict:
        return await asyncio.to_thread(
            self._request_sync, method, path, body, authorize=authorize
        )

    def _request_sync(
        self,
        method: str,
        path: str,
        body: dict | None,
        *,
        authorize: bool,
    ) -> dict:
        headers = {
            "apikey": self._api_key,
            "Content-Type": "application/json",
        }
        if authorize:
            headers["Authorization"] = f"Bearer {self._api_key}"
        request = urllib.request.Request(  # noqa: S310
            f"{self._base_url}/{path}",
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
                f"Supabase Auth request failed ({exc.code}): {detail}"
            ) from exc
        except urllib.error.URLError as exc:
            raise AuthGatewayError(
                f"Supabase Auth request failed: {exc.reason}"
            ) from exc
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AuthGatewayError("Supabase Auth returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise AuthGatewayError("Supabase Auth returned an invalid response")
        return payload


class SupabasePasswordAuthGateway(_SupabaseHttpGateway, PasswordAuthGateway):
    """Exchange Administrator credentials through Supabase GoTrue."""

    def __init__(self, supabase_url: str, publishable_key: str) -> None:
        """Initialize password authentication endpoint."""
        super().__init__(f"{supabase_url.rstrip('/')}/auth/v1", publishable_key)

    async def issue_access_token(self, email: str, password: str) -> str:
        """Authenticate password credentials and return access token."""
        payload = await self._request(
            "POST",
            "token?grant_type=password",
            {"email": email, "password": password},
        )
        token = payload.get("access_token")
        if not isinstance(token, str) or not token:
            raise AuthGatewayError("Supabase Auth response has no access token")
        return token


class SupabaseAuthAdminGateway(_SupabaseHttpGateway, AuthAdminGateway):
    """Administer Supabase Auth users with service-role credentials."""

    def __init__(self, supabase_url: str, service_role_key: str) -> None:
        """Initialize trusted Auth Admin endpoint."""
        super().__init__(f"{supabase_url.rstrip('/')}/auth/v1/admin", service_role_key)

    async def invite(self, email: str) -> dict:
        """Send invitation and return invited user."""
        payload = await self._request(
            "POST", "invite", {"email": email}, authorize=True
        )
        user = payload.get("user", payload)
        if not isinstance(user, dict):
            raise AuthGatewayError("Supabase invitation returned no user")
        return user

    async def find_by_email(self, email: str) -> dict | None:
        """Find one user by exact case-insensitive email."""
        query = urllib.parse.urlencode({"filter": email})
        payload = await self._request("GET", f"users?{query}", authorize=True)
        users = payload.get("users")
        if not isinstance(users, list):
            raise AuthGatewayError("Supabase user search returned invalid data")
        normalized = email.casefold()
        return next(
            (
                user
                for user in users
                if isinstance(user, dict)
                and isinstance(user.get("email"), str)
                and user["email"].casefold() == normalized
            ),
            None,
        )

    async def set_role(self, user_id: str, role: str | None) -> None:
        """Set or remove ``app_metadata.marquise_role``."""
        await self._request(
            "PUT",
            f"users/{user_id}",
            {"app_metadata": {"marquise_role": role}},
            authorize=True,
        )

    async def delete(self, user_id: str) -> None:
        """Delete one user."""
        await self._request("DELETE", f"users/{user_id}", authorize=True)
