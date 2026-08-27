"""Screening read endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi_cache.decorator import cache
from fastapi_pagination import Page, Params

from marquise import GetScreeningUseCase, SearchScreeningsUseCase
from marquise_api.dependencies import (
    get_screening_use_case,
    get_search_screenings_use_case,
)
from marquise_api.openapi_responses import error_responses
from marquise_api.rate_limit import current_rate_limit, limiter
from marquise_api.schemas import ScreeningResponse

router = APIRouter(tags=["screenings"])


@router.get(
    "/screenings",
    response_model=Page[ScreeningResponse],
    responses=error_responses(422, 429),
)
@limiter.limit(current_rate_limit)
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
    use_case: SearchScreeningsUseCase = Depends(get_search_screenings_use_case),
) -> Page[ScreeningResponse]:
    """Search screenings across all cinemas by any combination of filters."""
    output = await use_case.execute(
        SearchScreeningsUseCase.InputData(
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
