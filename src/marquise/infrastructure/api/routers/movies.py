"""Movie read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from marquise.application.exceptions import MovieNotFoundError
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.infrastructure.api.cache import TTLCache, cached
from marquise.infrastructure.api.dependencies import get_cache, get_container
from marquise.infrastructure.api.schemas import MovieResponse
from marquise.infrastructure.di.container import Container

router = APIRouter(tags=["movies"])


@router.get("/movies/{movie_id}", response_model=MovieResponse)
@cached("get_movie", key_params=("movie_id",))
async def get_movie(
    movie_id: str,
    container: Container = Depends(get_container),
    cache: TTLCache = Depends(get_cache),
) -> MovieResponse:
    """Retrieve a single movie by its ID."""
    use_case = container.get_movie_use_case
    try:
        output = await use_case.execute(GetMovieUseCase.InputData(movie_id=movie_id))
    except MovieNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MovieResponse.model_validate(output)
