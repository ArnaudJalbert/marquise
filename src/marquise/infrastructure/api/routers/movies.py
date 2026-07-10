"""Movie read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi_cache.decorator import cache

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.infrastructure.api.dependencies import get_container
from marquise.infrastructure.api.rate_limit import current_rate_limit, limiter
from marquise.infrastructure.api.schemas import MovieResponse
from marquise.infrastructure.di.container import Container

router = APIRouter(tags=["movies"])


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
