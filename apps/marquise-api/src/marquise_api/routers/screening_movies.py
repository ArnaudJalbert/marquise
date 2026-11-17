"""Bounded movie-first listing of upcoming screenings and its daily volume."""

from datetime import date
from math import ceil
from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from marquise import BrowseScreeningMoviesQuery, CountScreeningDaysQuery
from marquise_api.dependencies import (
    get_browse_screening_movies_query,
    get_count_screening_days_query,
)
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


class ScreeningDayCount(BaseModel):
    """Matching screening occurrences on one Montréal date."""

    date: date
    screenings: int = Field(ge=0)


class ScreeningDayCounts(BaseModel):
    """One total for every date of the requested horizon, in order."""

    days: list[ScreeningDayCount]


@router.post(
    "/screening-movies",
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
            hours=BrowseScreeningMoviesQuery.HourFilterInput(
                ranges=tuple(
                    BrowseScreeningMoviesQuery.HourRangeInput(item.start, item.end)
                    for item in hour_filter.ranges
                ),
                excluded=hour_filter.operator == "is_not",
            )
            if hour_filter
            else None,
            excluded_cinemas=tuple(exclude_cinema or ()),
        )
    )
    return ScreeningMoviePage(
        items=[ScreeningMovieResponse.model_validate(movie) for movie in result.movies],
        total=result.total,
        page=page,
        pages=ceil(result.total / 24),
    )


class ScreeningDayCountParams(BaseModel):
    """An inclusive Montréal horizon and the listing's query filters."""

    start: date
    end: date
    title: str | None = Field(default=None, max_length=200)
    cinema: list[str] = []
    exclude_cinema: list[str] = []
    language: list[str] = []

    @model_validator(mode="after")
    def _validate_order(self) -> Self:
        if self.start > self.end:
            raise ValueError("Invalid screening filter range")
        return self


@router.post(
    "/screening-day-counts",
    response_model=ScreeningDayCounts,
    responses=error_responses(422, 429),
)
@limiter.limit(current_rate_limit)
async def count_screening_days(
    request: Request,
    response: Response,
    params: Annotated[ScreeningDayCountParams, Query()],
    filters: ScreeningMovieFilters,
    query: CountScreeningDaysQuery = Depends(get_count_screening_days_query),
) -> ScreeningDayCounts:
    """Count screenings per inclusive Montreal date with the listing's filters.

    Every date up to 42 days is returned, zero included. Started screenings are
    excluded, so this endpoint is uncached like the listing.
    """
    result = await query.execute(_to_count_input(params, filters))
    return ScreeningDayCounts(
        days=[
            ScreeningDayCount(date=day.date, screenings=day.screenings)
            for day in result.days
        ]
    )


def _to_count_input(
    params: ScreeningDayCountParams, filters: ScreeningMovieFilters
) -> CountScreeningDaysQuery.InputData:
    hours = None if filters.hours is None else _to_count_hours(filters.hours)
    return CountScreeningDaysQuery.InputData(
        start=params.start,
        end=params.end,
        title=params.title,
        cinemas=tuple(params.cinema),
        languages=tuple(params.language),
        hours=hours,
        excluded_cinemas=tuple(params.exclude_cinema),
    )


def _to_count_hours(
    hour_filter: HourFilterRequest,
) -> CountScreeningDaysQuery.HourFilterInput:
    return CountScreeningDaysQuery.HourFilterInput(
        ranges=tuple(
            CountScreeningDaysQuery.HourRangeInput(item.start, item.end)
            for item in hour_filter.ranges
        ),
        excluded=hour_filter.operator == "is_not",
    )
