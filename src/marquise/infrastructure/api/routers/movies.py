"""Movie read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi_cache.decorator import cache
from fastapi_pagination import Page, Params

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
from marquise.infrastructure.api.dependencies import get_container
from marquise.infrastructure.api.rate_limit import current_rate_limit, limiter
from marquise.infrastructure.api.schemas import MovieResponse
from marquise.infrastructure.di.container import Container

router = APIRouter(tags=["movies"])


@router.get("/movies", response_model=Page[MovieResponse])
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


@router.get("/movies/{movie_id}", response_model=MovieResponse)
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
    try:
        output = await use_case.execute(GetMovieUseCase.InputData(movie_id=movie_id))
    except MovieNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MovieResponse.model_validate(output)
