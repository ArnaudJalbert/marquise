"""Cinema read endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi_cache.decorator import cache
from fastapi_pagination import Page, Params

from marquise import CinemaController
from marquise_api.dependencies import get_cinema_controller
from marquise_api.openapi_responses import error_responses
from marquise_api.rate_limit import current_rate_limit, limiter
from marquise_api.routers._dependencies import resolve_showtimes_date_range
from marquise_api.schemas import (
    CinemaResponse,
    MovieResponse,
    ScreeningResponse,
)

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
    controller: CinemaController = Depends(get_cinema_controller),
) -> Page[CinemaResponse]:
    """List cinemas, optionally filtered by name."""
    output = await controller.list(name=name, page=params.page, size=params.size)
    return Page.create(
        items=[CinemaResponse.model_validate(c) for c in output.cinemas],
        total=output.total,
        params=params,
    )


@router.get(
    "/cinemas/{cinema_id}",
    response_model=CinemaResponse,
    responses=error_responses(404, 422, 429),
)
@limiter.limit(current_rate_limit)
@cache()
async def get_cinema(
    request: Request,
    response: Response,
    cinema_id: str,
    controller: CinemaController = Depends(get_cinema_controller),
) -> CinemaResponse:
    """Retrieve a single cinema by its ID."""
    output = await controller.get(cinema_id=cinema_id)
    return CinemaResponse.model_validate(output)


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
    params: Params = Depends(),
    controller: CinemaController = Depends(get_cinema_controller),
) -> Page[ScreeningResponse]:
    """List all of a cinema's screenings.

    No filtering beyond the cinema itself — use ``GET /v1/screenings`` for
    date range, movie, or language filters.
    """
    output = await controller.get_screenings(
        cinema_id=cinema_id,
        page=params.page,
        size=params.size,
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
    controller: CinemaController = Depends(get_cinema_controller),
) -> Page[MovieResponse]:
    """List the distinct movies currently screening at a cinema."""
    from_, to = date_range
    output = await controller.get_movies(
        cinema_id=cinema_id,
        start_date=from_,
        end_date=to,
        page=params.page,
        size=params.size,
    )

    return Page.create(
        items=[MovieResponse.model_validate(m) for m in output.movies],
        total=output.total,
        params=params,
    )
