"""Movie read endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi_cache.decorator import cache
from fastapi_pagination import Page, Params

from marquise import GetMovieScreeningsQuery, GetMovieUseCase, ListMoviesUseCase
from marquise_api.dependencies import (
    get_list_movies_use_case,
    get_movie_screenings_query,
    get_movie_use_case,
)
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
        default=None,
        description=(
            "Filter movies by title (case-insensitive substring)."
            " May be combined with ids to filter within that set."
        ),
    ),
    ids: list[str] | None = Query(
        default=None,
        description=(
            "Fetch specific movies in bulk, repeated per ID (?ids=a&ids=b)."
            " May be combined with title to filter within that set. At most"
            " 100 ids, and the count must not exceed size. IDs with no"
            " matching movie are silently omitted from the response."
        ),
    ),
    params: Params = Depends(),
    use_case: ListMoviesUseCase = Depends(get_list_movies_use_case),
) -> Page[MovieResponse]:
    """List movies, optionally filtered by title and/or fetched in bulk by ids."""
    output = await use_case.execute(
        ListMoviesUseCase.InputData(
            title=title,
            ids=tuple(ids) if ids is not None else None,
            page=params.page,
            size=params.size,
        )
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
    use_case: GetMovieUseCase = Depends(get_movie_use_case),
) -> MovieResponse:
    """Retrieve a single movie by its ID."""
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
    query: GetMovieScreeningsQuery = Depends(get_movie_screenings_query),
) -> Page[ScreeningResponse]:
    """List all of a movie's screenings.

    No filtering beyond the movie itself — use ``GET /v1/screenings`` for
    date range, cinema, or language filters.
    """
    output = await query.execute(
        GetMovieScreeningsQuery.InputData(
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
