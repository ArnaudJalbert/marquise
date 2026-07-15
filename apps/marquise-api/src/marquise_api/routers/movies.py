"""Movie read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi_cache.decorator import cache
from fastapi_pagination import Page, Params

from marquise import MovieController
from marquise_api.dependencies import get_movie_controller
from marquise_api.openapi_responses import error_responses
from marquise_api.rate_limit import current_rate_limit, limiter
from marquise_api.schemas import MovieResponse, ScreeningResponse

router = APIRouter(tags=["movies"])


@router.get(
    "/movies",
    response_model=Page[MovieResponse],
    responses=error_responses(422, 429),
)
@limiter.limit(current_rate_limit)
@cache()
async def list_movies(
    request: Request,
    response: Response,
    title: str | None = Query(
        default=None, description="Filter movies by title (case-insensitive)."
    ),
    params: Params = Depends(),
    controller: MovieController = Depends(get_movie_controller),
) -> Page[MovieResponse]:
    """List movies, optionally filtered by title."""
    output = await controller.list(title=title, page=params.page, size=params.size)
    return Page.create(
        items=[MovieResponse.model_validate(m) for m in output.movies],
        total=output.total,
        params=params,
    )


@router.get(
    "/movies/{movie_id}",
    response_model=MovieResponse,
    responses=error_responses(404, 422, 429),
)
@limiter.limit(current_rate_limit)
@cache()
async def get_movie(
    request: Request,
    response: Response,
    movie_id: str,
    controller: MovieController = Depends(get_movie_controller),
) -> MovieResponse:
    """Retrieve a single movie by its ID."""
    output = await controller.get(movie_id=movie_id)
    return MovieResponse.model_validate(output)


@router.get(
    "/movies/{movie_id}/screenings",
    response_model=Page[ScreeningResponse],
    responses=error_responses(404, 422, 429),
)
@limiter.limit(current_rate_limit)
@cache()
async def get_movie_screenings(
    request: Request,
    response: Response,
    movie_id: str,
    params: Params = Depends(),
    controller: MovieController = Depends(get_movie_controller),
) -> Page[ScreeningResponse]:
    """List all of a movie's screenings.

    No filtering beyond the movie itself — use ``GET /v1/screenings`` for
    date range, cinema, or language filters.
    """
    output = await controller.get_screenings(
        movie_id=movie_id,
        page=params.page,
        size=params.size,
    )
    return Page.create(
        items=[ScreeningResponse.model_validate(s) for s in output.screenings],
        total=output.total,
        params=params,
    )
