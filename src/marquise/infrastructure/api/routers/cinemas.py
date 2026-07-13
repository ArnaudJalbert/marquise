"""Cinema read endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi_cache.decorator import cache
from fastapi_pagination import Page, Params

from marquise.application.use_cases.get_cinema_movies import GetCinemaMoviesUseCase
from marquise.application.use_cases.get_cinema_screenings import (
    GetCinemaScreeningsUseCase,
)
from marquise.infrastructure.api.dependencies import get_container
from marquise.infrastructure.api.openapi_responses import error_responses
from marquise.infrastructure.api.rate_limit import current_rate_limit, limiter
from marquise.infrastructure.api.routers._dependencies import (
    resolve_showtimes_date_range,
)
from marquise.infrastructure.api.schemas import (
    CinemaResponse,
    MovieResponse,
    ScreeningResponse,
)
from marquise.infrastructure.di.container import Container

router = APIRouter(tags=["cinemas"])


@router.get(
    "/cinemas",
    response_model=Page[CinemaResponse],
    responses=error_responses(422, 429),
)
@limiter.limit(current_rate_limit)
@cache()
async def list_cinemas(
    request: Request,
    response: Response,
    name: str | None = Query(
        default=None, description="Filter cinemas by name (case-insensitive)."
    ),
    params: Params = Depends(),
    container: Container = Depends(get_container),
) -> Page[CinemaResponse]:
    """List cinemas, optionally filtered by name."""
    output = await container.cinema_controller.list(
        name=name, page=params.page, size=params.size
    )
    return Page.create(
        items=[CinemaResponse.model_validate(c) for c in output.cinemas],
        total=output.total,
        params=params,
    )


@router.get(
    "/cinemas/{cinema_id}/screenings",
    response_model=Page[ScreeningResponse],
    responses=error_responses(404, 422, 429),
)
@limiter.limit(current_rate_limit)
@cache()
async def get_cinema_screenings(
    request: Request,
    response: Response,
    cinema_id: str,
    date_range: tuple[datetime, datetime] = Depends(resolve_showtimes_date_range),
    movie_id: str | None = Query(default=None, description="Filter by exact movie ID."),
    language: str | None = Query(
        default=None, description="Filter by exact language/subtitle version."
    ),
    params: Params = Depends(),
    container: Container = Depends(get_container),
) -> Page[ScreeningResponse]:
    """List a cinema's screenings within a date range."""
    from_, to = date_range
    use_case = container.get_cinema_screenings_use_case
    output = await use_case.execute(
        GetCinemaScreeningsUseCase.InputData(
            cinema_id=cinema_id,
            start_date=from_,
            end_date=to,
            movie_id=movie_id,
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
    "/cinemas/{cinema_id}/movies",
    response_model=Page[MovieResponse],
    responses=error_responses(404, 422, 429),
)
@limiter.limit(current_rate_limit)
@cache()
async def get_cinema_movies(
    request: Request,
    response: Response,
    cinema_id: str,
    date_range: tuple[datetime, datetime] = Depends(resolve_showtimes_date_range),
    params: Params = Depends(),
    container: Container = Depends(get_container),
) -> Page[MovieResponse]:
    """List the distinct movies currently screening at a cinema."""
    from_, to = date_range
    use_case = container.get_cinema_movies_use_case
    output = await use_case.execute(
        GetCinemaMoviesUseCase.InputData(
            cinema_id=cinema_id,
            start_date=from_,
            end_date=to,
            page=params.page,
            size=params.size,
        )
    )

    return Page.create(
        items=[MovieResponse.model_validate(m) for m in output.movies],
        total=output.total,
        params=params,
    )
