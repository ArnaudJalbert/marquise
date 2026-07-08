"""Cinema read endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from marquise.application.exceptions import CinemaNotFoundError
from marquise.application.use_cases.get_cinema_showtimes import (
    GetCinemaShowtimesUseCase,
)
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
from marquise.infrastructure.api.cache import TTLCache, cached
from marquise.infrastructure.api.dependencies import get_cache, get_container
from marquise.infrastructure.api.schemas import (
    CinemaResponse,
    CinemaShowtimesResponse,
)
from marquise.infrastructure.di.container import Container

router = APIRouter(tags=["cinemas"])


@router.get("/cinemas", response_model=list[CinemaResponse])
@cached("list_cinemas", key_params=("name",))
async def list_cinemas(
    name: str | None = Query(
        default=None, description="Filter cinemas by name (case-insensitive)."
    ),
    container: Container = Depends(get_container),
    cache: TTLCache = Depends(get_cache),
) -> list[CinemaResponse]:
    """List cinemas, optionally filtered by name."""
    use_case = container.list_cinemas_use_case
    output = await use_case.execute(ListCinemasUseCase.InputData(name=name))
    return [CinemaResponse.model_validate(c) for c in output.cinemas]


@router.get(
    "/cinemas/{cinema_id}/showtimes",
    response_model=CinemaShowtimesResponse,
)
@cached("get_cinema_showtimes", key_params=("cinema_id", "from_", "to"))
async def get_cinema_showtimes(
    cinema_id: str,
    from_: datetime = Query(alias="from", description="Start of range (inclusive)."),
    to: datetime = Query(description="End of range (inclusive)."),
    container: Container = Depends(get_container),
    cache: TTLCache = Depends(get_cache),
) -> CinemaShowtimesResponse:
    """List a cinema's screenings within a date range."""
    use_case = container.get_cinema_showtimes_use_case
    try:
        output = await use_case.execute(
            GetCinemaShowtimesUseCase.InputData(
                cinema_id=cinema_id,
                start_date=from_,
                end_date=to,
            )
        )
    except CinemaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CinemaShowtimesResponse.model_validate(output)
