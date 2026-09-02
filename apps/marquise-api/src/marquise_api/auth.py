"""Supabase JWT authentication and Marquise role dependencies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

import jwt
from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

MarquiseRole = Literal["member", "editor", "administrator"]
_VALID_ROLES = ("member", "editor", "administrator")
_bearer = HTTPBearer(auto_error=False)


class TokenVerificationError(ValueError):
    """Raised when a bearer token cannot identify a Marquise caller."""


@dataclass(frozen=True)
class AuthenticatedCaller:
    """Identity and Marquise role extracted from a verified access JWT."""

    subject: str
    role: MarquiseRole


class SigningKeyProvider(ABC):
    """Resolve trusted signing key for encoded JWT."""

    @abstractmethod
    def get_signing_key(self, token: str) -> jwt.PyJWK:
        """Return key matching token header."""


class TokenVerifier(ABC):
    """Verify bearer token and return authenticated caller."""

    @abstractmethod
    def verify(self, token: str) -> AuthenticatedCaller:
        """Validate token and return trusted caller claims."""


class SupabaseSigningKeyProvider(SigningKeyProvider):
    """Resolve signing keys through an injected Supabase JWKS client."""

    def __init__(self, client: jwt.PyJWKClient) -> None:
        self._client = client

    def get_signing_key(self, token: str) -> jwt.PyJWK:
        """Return signing key selected by token key ID."""
        return self._client.get_signing_key_from_jwt(token)


class SupabaseJwtVerifier(TokenVerifier):
    """Validate Supabase access JWT and required Marquise claims."""

    def __init__(
        self,
        signing_key_provider: SigningKeyProvider,
        issuer: str,
        audience: str = "authenticated",
    ) -> None:
        self._signing_key_provider = signing_key_provider
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str) -> AuthenticatedCaller:
        """Validate signature and claims, then return authenticated caller."""
        try:
            key = self._signing_key_provider.get_signing_key(token)
            claims: dict = jwt.decode(
                token,
                key=key,
                algorithms=[key.algorithm_name],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenVerificationError("Token has expired") from exc
        except jwt.InvalidIssuerError as exc:
            raise TokenVerificationError("Token has invalid issuer") from exc
        except jwt.InvalidAudienceError as exc:
            raise TokenVerificationError("Token has invalid audience") from exc
        except (jwt.PyJWTError, ValueError) as exc:
            raise TokenVerificationError("Token is invalid") from exc

        metadata = claims.get("app_metadata")
        role = metadata.get("marquise_role") if isinstance(metadata, dict) else None
        if role not in _VALID_ROLES:
            raise TokenVerificationError("Token has invalid Marquise role")

        subject = claims["sub"]
        if not isinstance(subject, str) or not subject:
            raise TokenVerificationError("Token has invalid subject")
        return AuthenticatedCaller(subject=subject, role=role)


def _authentication_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_token_verifier(request: Request) -> TokenVerifier:
    """Return verifier injected at application composition root."""
    verifier: TokenVerifier | None = request.app.state.token_verifier
    if verifier is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    return verifier


def require_authenticated(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    verifier: TokenVerifier = Depends(get_token_verifier),
) -> AuthenticatedCaller:
    """Require valid bearer token with any Marquise role."""
    if credentials is None:
        raise _authentication_error("Missing bearer token")
    try:
        return verifier.verify(credentials.credentials)
    except TokenVerificationError as exc:
        raise _authentication_error("Invalid bearer token") from exc


def require_editor(
    caller: AuthenticatedCaller = Depends(require_authenticated),
) -> AuthenticatedCaller:
    """Require Editor role; Administrators inherit Editor authorization."""
    if caller.role not in {"editor", "administrator"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor role required",
        )
    return caller


def require_administrator(
    caller: AuthenticatedCaller = Depends(require_authenticated),
) -> AuthenticatedCaller:
    """Require Administrator role."""
    if caller.role != "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return caller
