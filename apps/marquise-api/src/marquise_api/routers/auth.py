"""Authentication endpoints: token issuance and caller identity."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from marquise_api.auth import (
    AuthenticatedCaller,
    InvalidCredentialsError,
    TokenIssuanceError,
    TokenIssuer,
    get_token_issuer,
    require_authenticated,
)
from marquise_api.openapi_responses import error_responses
from marquise_api.rate_limit import current_rate_limit, limiter
from marquise_api.schemas import LoginRequest, LoginResponse, MeResponse

logger = logging.getLogger(__name__)

#: Per-IP ceiling for the only password-accepting surface, tighter than the
#: shared read limit to slow credential guessing. ponytail: single shared
#: counter per worker; per-credential or distributed limits if abuse appears.
LOGIN_RATE_LIMIT = "10/minute"

router = APIRouter(tags=["auth"])


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    responses=error_responses(401, 422, 429, 503),
)
@limiter.limit(LOGIN_RATE_LIMIT)
async def login(
    request: Request,
    response: Response,
    credentials: LoginRequest,
    issuer: TokenIssuer = Depends(get_token_issuer),
) -> LoginResponse:
    """Exchange email and password for a Supabase access token."""
    try:
        session = await issuer.issue(credentials.email, credentials.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except TokenIssuanceError as exc:
        logger.warning("Token issuance failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The authentication service is unavailable",
        ) from exc
    return LoginResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        token_type=session.token_type,
    )


@router.get(
    "/auth/me",
    response_model=MeResponse,
    responses=error_responses(401, 429),
)
@limiter.limit(current_rate_limit)
async def me(
    request: Request,
    response: Response,
    caller: AuthenticatedCaller = Depends(require_authenticated),
) -> MeResponse:
    """Return the authenticated caller's identity and role."""
    return MeResponse(subject=caller.subject, role=caller.role)
