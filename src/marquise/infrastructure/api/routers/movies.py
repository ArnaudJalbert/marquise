"""Movie read endpoints."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Depends, HTTPException

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.infrastructure.api.cache import TTLCache
from marquise.infrastructure.api.dependencies import get_cache, get_container
from marquise.infrastructure.api.schemas import MovieResponse
from marquise.infrastructure.di.container import Container

router = APIRouter(tags=["movies"])


@router.get("/movies/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: str,
    container: Container = Depends(get_container),
    cache: TTLCache = Depends(get_cache),
) -> MovieResponse:
    """Retrieve a single movie by its ID."""
    cache_key = ("get_movie", movie_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return cast(MovieResponse, cached)

    use_case = container.get_movie_use_case
    try:
        output = await use_case.execute(GetMovieUseCase.InputData(movie_id=movie_id))
    except MovieNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    result = MovieResponse.model_validate(output)
    cache.set(cache_key, result)
    return result
