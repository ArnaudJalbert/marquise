"""Bounded movie-first listing of upcoming screenings and its daily volume."""

from collections.abc import Callable
from datetime import date
from math import ceil
from typing import Annotated, Literal, Self

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from marquise import (
    BrowseScreeningMoviesQuery,
    CountScreeningDaysQuery,
    MarquiseFactory,
)
from marquise_api.dependencies import get_factory
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
    size: int
    pages: int


class ScreeningDayCount(BaseModel):
    """Matching screening occurrences on one Montréal date."""

    date: date
    screenings: int = Field(ge=0)


class ScreeningDayCounts(BaseModel):
    """One total for every date of the requested horizon, in order."""

    days: list[ScreeningDayCount]


class ScreeningMovieParams(BaseModel):
    """Inclusive Montréal dates, open-ended without end, and the query filters."""

    start: date
    end: date | None = None
    title: str | None = Field(default=None, max_length=200)
    cinema: list[str] = []
    exclude_cinema: list[str] = []
    language: list[str] = []

    @model_validator(mode="after")
    def _validate_order(self) -> Self:
        if self.end is not None and self.start > self.end:
            raise ValueError("Invalid screening filter range")
        return self


class BrowseScreeningMovieParams(ScreeningMovieParams):
    """The listing's dates and filters, and one page of movies."""

    page: int = Field(ge=1)
    size: int = Field(ge=1, le=100)


@router.post(
    "/screening-movies",
    response_model=ScreeningMoviePage,
    responses=error_responses(422, 429),
)
@limiter.limit(current_rate_limit)
async def browse_screening_movies(
    request: Request,
    response: Response,
    params: Annotated[BrowseScreeningMovieParams, Query()],
    filters: ScreeningMovieFilters,
    factory: MarquiseFactory = Depends(get_factory),
) -> ScreeningMoviePage:
    """List one page of distinct upcoming movies in inclusive Montreal dates.

    This endpoint is uncached so upcoming eligibility uses the current request's
    clock rather than a cached response's clock.
    """
    hours = filters.hours
    result = await factory.screenings.browse_screening_movies_query.execute(
        BrowseScreeningMoviesQuery.InputData(
            start=params.start,
            end=params.end,
            page=params.page,
            size=params.size,
            title=params.title,
            cinemas=tuple(params.cinema),
            languages=tuple(params.language),
            hours=None
            if hours is None
            else _to_hour_filter_input(
                hours,
                BrowseScreeningMoviesQuery.HourFilterInput,
                BrowseScreeningMoviesQuery.HourRangeInput,
            ),
            excluded_cinemas=tuple(params.exclude_cinema),
        )
    )
    return ScreeningMoviePage(
        items=[ScreeningMovieResponse.model_validate(movie) for movie in result.movies],
        total=result.total,
        page=params.page,
        size=params.size,
        pages=ceil(result.total / params.size),
    )


class ScreeningDayCountParams(ScreeningMovieParams):
    """An inclusive Montréal horizon and the listing's query filters."""

    end: date


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
    factory: MarquiseFactory = Depends(get_factory),
) -> ScreeningDayCounts:
    """Count screenings per inclusive Montreal date with the listing's filters.

    Every date up to 42 days is returned, zero included. Started screenings are
    excluded, so this endpoint is uncached like the listing.
    """
    result = await factory.screenings.count_screening_days_query.execute(
        _to_count_input(params, filters)
    )
    return ScreeningDayCounts(
        days=[
            ScreeningDayCount(date=day.date, screenings=day.screenings)
            for day in result.days
        ]
    )


def _to_count_input(
    params: ScreeningDayCountParams, filters: ScreeningMovieFilters
) -> CountScreeningDaysQuery.InputData:
    hours = filters.hours
    return CountScreeningDaysQuery.InputData(
        start=params.start,
        end=params.end,
        title=params.title,
        cinemas=tuple(params.cinema),
        languages=tuple(params.language),
        hours=None
        if hours is None
        else _to_hour_filter_input(
            hours,
            CountScreeningDaysQuery.HourFilterInput,
            CountScreeningDaysQuery.HourRangeInput,
        ),
        excluded_cinemas=tuple(params.exclude_cinema),
    )


def _to_hour_filter_input[FilterInput, RangeInput](
    hours: HourFilterRequest,
    filter_input: Callable[[tuple[RangeInput, ...], bool], FilterInput],
    range_input: Callable[[int, int], RangeInput],
) -> FilterInput:
    """Map the request hour filter to one query's hour input.

    Both queries turn their input into the domain ``HourFilter``. The facade
    keeps domain types out of the API, so the caller passes the query's own
    ``HourFilterInput`` and ``HourRangeInput``.

    Args:
        hours: The validated request hour filter.
        filter_input: The query's ``HourFilterInput`` class.
        range_input: The query's ``HourRangeInput`` class.

    Returns:
        The query's hour input, excluded when the operator is ``is_not``.
    """
    ranges = tuple(range_input(item.start, item.end) for item in hours.ranges)
    return filter_input(ranges, hours.operator == "is_not")
