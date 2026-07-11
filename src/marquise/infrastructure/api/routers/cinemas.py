"""Cinema read endpoints."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi_cache.decorator import cache
from fastapi_pagination import Page, Params

from marquise.application.use_cases.get_cinema_showtimes import (
    GetCinemaShowtimesUseCase,
)
from marquise.infrastructure.api.dependencies import get_container
from marquise.infrastructure.api.rate_limit import current_rate_limit, limiter
from marquise.infrastructure.api.schemas import CinemaResponse, ScreeningResponse
from marquise.infrastructure.di.container import Container

router = APIRouter(tags=["cinemas"])


def _start_of_today_utc() -> datetime:
    """Return the current UTC date at midnight, timezone-aware.

    Returns:
        A timezone-aware ``datetime`` for today's date at 00:00 UTC.
    """
    now = datetime.now(UTC)
    return datetime(now.year, now.month, now.day, tzinfo=UTC)


def resolve_showtimes_date_range(
    from_: datetime | None = Query(
        default=None,
        alias="from",
        description="Start of range (inclusive). Defaults to the start of today (UTC).",
    ),
    to: datetime | None = Query(
        default=None,
        description="End of range (inclusive). Defaults to one week from start.",
    ),
) -> tuple[datetime, datetime]:
    """Resolve the effective showtimes date range, applying defaults.

    Defaults are resolved here, as a dependency, rather than inside the
    cached endpoint body: fastapi-cache2 builds its cache key from the
    arguments FastAPI already resolved before the endpoint runs, so if
    ``from``/``to`` stayed ``None`` until the function body ran, every
    request that omits them would collide on one cache entry frozen at
    whichever moment first populated it.

    Returns:
        A ``(start, end)`` tuple, both timezone-aware.
    """
    resolved_from = from_ if from_ is not None else _start_of_today_utc()
    resolved_to = to if to is not None else resolved_from + timedelta(days=7)
    return resolved_from, resolved_to


@router.get("/cinemas", response_model=Page[CinemaResponse])
@limiter.limit(current_rate_limit)
@cache()
async def list_cinemas(
    request: Request,
    response: Response,
    name: str | None = Query(
        default=None, description="Filter cinemas by name (case-insensitive)."
    ),
    params: Params = Depends(),
    container: Container = Depends(get_container),
) -> Page[CinemaResponse]:
    """List cinemas, optionally filtered by name."""
    output = await container.cinema_controller.list(
        name=name, page=params.page, size=params.size
    )
    return Page.create(
        items=[CinemaResponse.model_validate(c) for c in output.cinemas],
        total=output.total,
        params=params,
    )


@router.get(
    "/cinemas/{cinema_id}/showtimes",
    response_model=Page[ScreeningResponse],
)
@limiter.limit(current_rate_limit)
@cache()
async def get_cinema_showtimes(
    request: Request,
    response: Response,
    cinema_id: str,
    date_range: tuple[datetime, datetime] = Depends(resolve_showtimes_date_range),
    params: Params = Depends(),
    container: Container = Depends(get_container),
) -> Page[ScreeningResponse]:
    """List a cinema's screenings within a date range."""
    from_, to = date_range
    use_case = container.get_cinema_showtimes_use_case
    output = await use_case.execute(
        GetCinemaShowtimesUseCase.InputData(
            cinema_id=cinema_id,
            start_date=from_,
            end_date=to,
            page=params.page,
            size=params.size,
        )
    )

    return Page.create(
        items=[ScreeningResponse.model_validate(s) for s in output.screenings],
        total=output.total,
        params=params,
    )
