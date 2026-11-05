"""Bounded movie-first listing of upcoming screenings."""

from datetime import date
from math import ceil
from typing import Literal, Self

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from marquise import BrowseScreeningMoviesQuery
from marquise_api.dependencies import get_browse_screening_movies_query
from marquise_api.openapi_responses import error_responses
from marquise_api.rate_limit import current_rate_limit, limiter
from marquise_api.schemas import MovieResponse, ScreeningResponse

router = APIRouter(tags=["movies"])


class HourRangeRequest(BaseModel):
    """One half-open whole-hour Montréal range."""

    model_config = ConfigDict(extra="forbid", strict=True)

    start: int = Field(ge=0, le=23)
    end: int = Field(ge=1, le=24)

    @model_validator(mode="after")
    def _validate_order(self) -> Self:
        if self.start >= self.end:
            raise ValueError("start must be before end")
        return self


class HourFilterRequest(BaseModel):
    """Ranges matched together before applying a comparison operator."""

    model_config = ConfigDict(extra="forbid", strict=True)

    operator: Literal["is", "is_not"]
    ranges: list[HourRangeRequest] = Field(min_length=1)


class ScreeningMovieFilters(BaseModel):
    """Structured filters for a screening-movie search."""

    model_config = ConfigDict(extra="forbid", strict=True)

    hours: HourFilterRequest | None = None


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


@router.post(
    "/screening-movies/search",
    response_model=ScreeningMoviePage,
    responses=error_responses(422, 429),
)
@limiter.limit(current_rate_limit)
async def browse_screening_movies(
    request: Request,
    response: Response,
    start: date,
    filters: ScreeningMovieFilters,
    end: date | None = None,
    page: int = Query(default=1, ge=1),
    title: str | None = Query(default=None, max_length=200),
    cinema: list[str] | None = Query(default=None),
    exclude_cinema: list[str] | None = Query(default=None),
    language: list[str] | None = Query(default=None),
    query: BrowseScreeningMoviesQuery = Depends(get_browse_screening_movies_query),
) -> ScreeningMoviePage:
    """List 24 distinct movies in inclusive Montreal dates, excluding started shows.

    This endpoint is uncached so upcoming eligibility uses the current request's
    clock rather than a cached response's clock.
    """
    if end is not None and start > end:
        raise HTTPException(status_code=422, detail="Invalid screening filter range")
    hour_filter = filters.hours
    result = await query.execute(
        BrowseScreeningMoviesQuery.InputData(
            start=start,
            end=end,
            page=page,
            title=title,
            cinemas=tuple(cinema or ()),
            languages=tuple(language or ()),
            hours=tuple((item.start, item.end) for item in hour_filter.ranges)
            if hour_filter
            else (),
            exclude_hours=hour_filter is not None and hour_filter.operator == "is_not",
            excluded_cinemas=tuple(exclude_cinema or ()),
        )
    )
    return ScreeningMoviePage(
        items=[ScreeningMovieResponse.model_validate(movie) for movie in result.movies],
        total=result.total,
        page=page,
        pages=ceil(result.total / 24),
    )
