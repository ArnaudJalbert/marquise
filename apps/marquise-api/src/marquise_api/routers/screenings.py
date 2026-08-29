"""Screening read endpoints."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from hashlib import sha256

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi_cache.decorator import cache
from fastapi_pagination import Page, Params

from marquise import GetScreeningUseCase, SearchScreeningsQuery
from marquise_api.dependencies import (
    get_screening_use_case,
    get_search_screenings_query,
)
from marquise_api.openapi_responses import error_responses
from marquise_api.rate_limit import current_rate_limit, limiter
from marquise_api.schemas import ScreeningResponse

router = APIRouter(tags=["screenings"])


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
    use_case: GetScreeningUseCase = Depends(get_screening_use_case),
) -> ScreeningResponse:
    """Retrieve a single screening by its ID."""
    output = await use_case.execute(
        GetScreeningUseCase.InputData(screening_id=screening_id)
    )
    return ScreeningResponse.model_validate(output)
