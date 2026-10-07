"""Public screening reads and authenticated screening mutation endpoints."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from hashlib import sha256

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi_cache.decorator import cache
from fastapi_pagination import Page, Params

from marquise import (
    CreateScreeningUseCase,
    DeleteScreeningUseCase,
    GetScreeningQuery,
    SearchScreeningsQuery,
    UpdateScreeningUseCase,
)
from marquise_api.auth import require_editor
from marquise_api.cache import invalidate_public_cache
from marquise_api.dependencies import (
    get_create_screening_use_case,
    get_delete_screening_use_case,
    get_screening_query,
    get_search_screenings_query,
    get_update_screening_use_case,
)
from marquise_api.openapi_responses import error_responses
from marquise_api.rate_limit import current_rate_limit, enforce_rate_limit, limiter
from marquise_api.schemas import ScreeningResponse
from marquise_api.schemas.screening import (
    CreateScreeningRequest,
    UpdateScreeningRequest,
)

router = APIRouter(tags=["screenings"])


@router.post(
    "/screenings",
    status_code=201,
    response_model=ScreeningResponse,
    responses={
        **error_responses(401, 403, 404, 409, 422, 429, 503),
        201: {
            "description": "Persisted screening (without external_id).",
            "headers": {
                "Location": {
                    "description": "Relative URL of the created screening detail.",
                    "schema": {"type": "string"},
                }
            },
        },
    },
    dependencies=[Depends(enforce_rate_limit), Depends(require_editor)],
)
@limiter.limit(current_rate_limit)
async def create_screening(
    request: Request,
    response: Response,
    body: CreateScreeningRequest,
    use_case: CreateScreeningUseCase = Depends(get_create_screening_use_case),
) -> ScreeningResponse:
    """Create a screening as an Editor or Administrator using existing movie/cinema IDs.

    Showtime must be timezone-aware; optional metadata may be omitted or null.
    The response is persisted data and is uncached. Successful writes clear the
    full instance-local public cache on a best-effort basis; failures to clear
    do not roll back or retry the committed write. Other instances rely on expiry.
    """
    output = await use_case.execute(
        CreateScreeningUseCase.InputData(**body.model_dump())
    )
    await invalidate_public_cache(request)
    response.headers["Location"] = f"/v1/screenings/{output.id}"
    return ScreeningResponse.model_validate(output)


@router.patch(
    "/screenings/{screening_id}",
    response_model=ScreeningResponse,
    responses=error_responses(401, 403, 404, 409, 422, 429, 503),
    dependencies=[Depends(enforce_rate_limit), Depends(require_editor)],
)
@limiter.limit(current_rate_limit)
async def update_screening(
    request: Request,
    response: Response,
    screening_id: str,
    body: UpdateScreeningRequest,
    use_case: UpdateScreeningUseCase = Depends(get_update_screening_use_case),
) -> ScreeningResponse:
    """Edit supplied fields as an Editor or Administrator, including movie/cinema/time.

    Omitted fields stay unchanged; null clears only optional metadata. Empty
    PATCH returns the existing screening (or 404) without cache invalidation.
    The persisted response is uncached. Nonempty successful edits clear the full
    instance-local public cache, best-effort; failures to clear never retry or
    roll back the write. Other instances rely on expiry.
    """
    output = await use_case.execute(
        UpdateScreeningUseCase.InputData(
            screening_id=screening_id, **body.model_dump(exclude_unset=True)
        )
    )
    if body.model_fields_set:
        await invalidate_public_cache(request)
    return ScreeningResponse.model_validate(output)


@router.delete(
    "/screenings/{screening_id}",
    status_code=204,
    responses=error_responses(401, 403, 404, 422, 429, 503),
    dependencies=[Depends(enforce_rate_limit), Depends(require_editor)],
)
@limiter.limit(current_rate_limit)
async def delete_screening(
    request: Request,
    response: Response,
    screening_id: str,
    use_case: DeleteScreeningUseCase = Depends(get_delete_screening_use_case),
) -> Response:
    """Permanently delete a screening and atomically remove its movie if orphaned.

    Editors and Administrators have identical global deletion permissions.
    A missing screening is an error, not an idempotent success. The response is
    uncached. Success clears the full instance-local public cache, best-effort;
    failure to clear never retries or rolls back deletion. Other instances rely
    on expiry.
    """
    await use_case.execute(DeleteScreeningUseCase.InputData(screening_id=screening_id))
    await invalidate_public_cache(request)
    response.status_code = 204
    return response


def _search_screenings_key_builder(
    func: Callable[..., object],
    namespace: str = "",
    *,
    request: Request | None = None,
    response: Response | None = None,
    args: tuple[object, ...],
    kwargs: dict[str, object],
) -> str:
    """Build a fixed-length cache key from the raw query string."""
    query = request.url.query if request is not None else ""
    digest = sha256(query.encode()).hexdigest()
    return f"{namespace}:{func.__module__}:{func.__name__}:{digest}"


@router.get(
    "/screenings",
    response_model=Page[ScreeningResponse],
    responses=error_responses(422, 429),
)
@limiter.limit(current_rate_limit)
@cache(key_builder=_search_screenings_key_builder)
async def search_screenings(
    request: Request,
    response: Response,
    movie: str | None = Query(
        default=None, description="Filter by movie title (case-insensitive)."
    ),
    movie_id: str | None = Query(default=None, description="Filter by exact movie ID."),
    cinema_id: str | None = Query(
        default=None, description="Filter by exact cinema ID."
    ),
    from_: datetime | None = Query(
        default=None,
        alias="from",
        description="Start of showtime range (inclusive). Unbounded if omitted.",
    ),
    to: datetime | None = Query(
        default=None,
        description="End of showtime range (inclusive). Unbounded if omitted.",
    ),
    language: str | None = Query(
        default=None, description="Filter by exact language/subtitle version."
    ),
    params: Params = Depends(),
    query: SearchScreeningsQuery = Depends(get_search_screenings_query),
) -> Page[ScreeningResponse]:
    """Search screenings across all cinemas by any combination of filters."""
    output = await query.execute(
        SearchScreeningsQuery.InputData(
            movie=movie,
            movie_id=movie_id,
            cinema_id=cinema_id,
            start_date=from_,
            end_date=to,
            language=language,
            page=params.page,
            size=params.size,
        )
    )
    return Page.create(
        items=[ScreeningResponse.model_validate(s) for s in output.screenings],
        total=output.total,
        params=params,
    )


@router.get(
    "/screenings/{screening_id}",
    response_model=ScreeningResponse,
    responses=error_responses(404, 422, 429),
)
@limiter.limit(current_rate_limit)
@cache()
async def get_screening(
    request: Request,
    response: Response,
    screening_id: str,
    query: GetScreeningQuery = Depends(get_screening_query),
) -> ScreeningResponse:
    """Retrieve a single screening by its ID."""
    output = await query.execute(GetScreeningQuery.InputData(screening_id=screening_id))
    return ScreeningResponse.model_validate(output)
