"""Movie read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi_cache.decorator import cache
from fastapi_pagination import Page, Params

from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.get_movie_screenings import (
    GetMovieScreeningsUseCase,
)
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.infrastructure.api.dependencies import get_container
from marquise.infrastructure.api.openapi_responses import error_responses
from marquise.infrastructure.api.rate_limit import current_rate_limit, limiter
from marquise.infrastructure.api.schemas import MovieResponse, ScreeningResponse
from marquise.infrastructure.di.container import Container

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
    container: Container = Depends(get_container),
) -> Page[MovieResponse]:
    """List movies, optionally filtered by title."""
    use_case = container.list_movies_use_case
    output = await use_case.execute(
        ListMoviesUseCase.InputData(title=title, page=params.page, size=params.size)
    )
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
    container: Container = Depends(get_container),
) -> MovieResponse:
    """Retrieve a single movie by its ID."""
    use_case = container.get_movie_use_case
    output = await use_case.execute(GetMovieUseCase.InputData(movie_id=movie_id))
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
    container: Container = Depends(get_container),
) -> Page[ScreeningResponse]:
    """List all of a movie's screenings.

    No filtering beyond the movie itself — use ``GET /v1/screenings`` for
    date range, cinema, or language filters.
    """
    use_case = container.get_movie_screenings_use_case
    output = await use_case.execute(
        GetMovieScreeningsUseCase.InputData(
            movie_id=movie_id,
            page=params.page,
            size=params.size,
        )
    )
    return Page.create(
        items=[ScreeningResponse.model_validate(s) for s in output.screenings],
        total=output.total,
        params=params,
    )
