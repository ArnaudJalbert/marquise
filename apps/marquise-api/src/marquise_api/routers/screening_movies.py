"""Bounded movie-first listing of upcoming screenings."""

from datetime import date
from math import ceil

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel

from marquise import BrowseScreeningMoviesQuery
from marquise_api.dependencies import get_browse_screening_movies_query
from marquise_api.openapi_responses import error_responses
from marquise_api.rate_limit import current_rate_limit, limiter
from marquise_api.schemas import MovieResponse, ScreeningResponse

router = APIRouter(tags=["movies"])


class ScreeningMovieResponse(MovieResponse):
    """Movie metadata and its next three matching screenings total."""

    screenings: list[ScreeningResponse]


class ScreeningMoviePage(BaseModel):
    """Authoritative distinct-movie pagination metadata."""

    items: list[ScreeningMovieResponse]
    total: int
    page: int
    size: int = 24
    pages: int


@router.get(
    "/screening-movies",
    response_model=ScreeningMoviePage,
    responses=error_responses(422, 429),
)
@limiter.limit(current_rate_limit)
async def browse_screening_movies(
    request: Request,
    response: Response,
    start: date,
    end: date,
    page: int = Query(default=1, ge=1),
    query: BrowseScreeningMoviesQuery = Depends(get_browse_screening_movies_query),
) -> ScreeningMoviePage:
    """List 24 distinct movies in inclusive Montreal dates, excluding started shows.

    This endpoint is uncached so upcoming eligibility uses the current request's
    clock rather than a cached response's clock.
    """
    result = await query.execute(
        BrowseScreeningMoviesQuery.InputData(start=start, end=end, page=page)
    )
    return ScreeningMoviePage(
        items=[ScreeningMovieResponse.model_validate(movie) for movie in result.movies],
        total=result.total,
        page=page,
        pages=ceil(result.total / 24),
    )
