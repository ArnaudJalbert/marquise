"""Request and response models for the authentication endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from marquise_api.auth import MarquiseRole

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class LoginRequest(BaseModel):
    """Email and password exchanged for a Supabase access token."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"email": "admin@example.com", "password": "hunter2"}]
        }
    )

    email: str = Field(
        description="The account email address.",
        pattern=_EMAIL_PATTERN,
        max_length=254,
    )
    password: str = Field(
        description="The account password.", min_length=1, max_length=256
    )


class LoginResponse(BaseModel):
    """Session tokens returned by a successful password sign-in."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "access_token": "eyJhbGciOiJSUzI1NiIs...",
                    "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
                    "expires_in": 900,
                    "token_type": "bearer",
                }
            ]
        }
    )

    access_token: str = Field(description="Bearer access token (JWT).")
    refresh_token: str | None = Field(
        default=None, description="Refresh token, when the provider issues one."
    )
    expires_in: int = Field(
        description="Access token lifetime in seconds from issuance."
    )
    token_type: str = Field(
        default="bearer", description="Token type, always `bearer`."
    )


class MeResponse(BaseModel):
    """Identity of the caller of an authenticated request."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "subject": "b1a8d5e2-...",
                    "role": "administrator",
                }
            ]
        }
    )

    subject: str = Field(description="Authenticated caller's user identifier.")
    role: MarquiseRole = Field(
        description="Marquise role carried by the caller's token."
    )
