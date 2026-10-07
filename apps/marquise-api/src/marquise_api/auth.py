"""FastAPI dependencies for Marquise authentication and authorization."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from marquise import (
    AuthenticationError,
    AuthenticationServiceUnavailableError,
    ScreeningWriteContext,
    VerifyAccessTokenQuery,
)
from marquise_api.dependencies import get_verify_access_token_query

_bearer = HTTPBearer(auto_error=False)

AuthenticatedCaller = VerifyAccessTokenQuery.OutputData


def _authentication_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _authentication_unavailable_error(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=detail,
    )


async def require_authenticated(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    query: VerifyAccessTokenQuery = Depends(get_verify_access_token_query),
) -> AuthenticatedCaller:
    """Require a verified token carrying any Marquise role."""
    if credentials is None:
        raise _authentication_error("Missing bearer token")
    try:
        return await query.execute(query.InputData(token=credentials.credentials))
    except AuthenticationServiceUnavailableError as exc:
        raise _authentication_unavailable_error(
            "Authentication service is unavailable"
        ) from exc
    except (AuthenticationError, ValueError) as exc:
        raise _authentication_error("Invalid bearer token") from exc


async def require_editor(
    caller: AuthenticatedCaller = Depends(require_authenticated),
) -> AuthenticatedCaller:
    """Require Editor authorization."""
    if not caller.can_edit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor role required",
        )
    return caller


async def get_screening_write_context(
    caller: AuthenticatedCaller = Depends(require_editor),
    key: str = Header(
        ...,
        alias="Idempotency-Key",
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._:-]+$",
        description=(
            "Unique account-scoped key. Reuse only for retries of the same "
            "request; successful keys do not expire."
        ),
    ),
    reason: str = Header(
        ...,
        alias="X-Change-Reason",
        min_length=1,
        max_length=500,
        description="Nonblank, credential-free reason with no control characters.",
    ),
) -> ScreeningWriteContext:
    """Map mandatory intent headers and verified identity into core input data."""
    return ScreeningWriteContext(account=caller.subject, key=key, reason=reason)


async def require_administrator(
    caller: AuthenticatedCaller = Depends(require_authenticated),
) -> AuthenticatedCaller:
    """Require Administrator authorization."""
    if not caller.can_administer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator role required",
        )
    return caller
