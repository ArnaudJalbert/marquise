"""The cinema movies route supplies timezone-aware use-case dates."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import create_autospec

import pytest
from fastapi.testclient import TestClient

from marquise import GetCinemaMoviesUseCase, MarquiseFactory
from marquise_api.app import create_app


@dataclass(frozen=True, slots=True)
class DateRangeCase:
    """Query dates and their literal expected use-case range."""

    from_param: str
    to_param: str
    expected_range: tuple[datetime, datetime]


@pytest.fixture
def factory() -> MarquiseFactory:
    """Provide a cinema movies use case that finds no movies."""
    factory = create_autospec(MarquiseFactory, instance=True)
    factory.get_cinema_movies_use_case = create_autospec(
        GetCinemaMoviesUseCase, instance=True
    )
    factory.get_cinema_movies_use_case.execute.return_value = (
        GetCinemaMoviesUseCase.OutputData(
            cinema_id="cin-date-contract", cinema_name="Cinema", movies=[], total=0
        )
    )
    return factory


@pytest.fixture
def client(factory: MarquiseFactory) -> TestClient:
    """Provide the API with its factory replaced."""
    return TestClient(create_app(factory=factory))


@pytest.mark.parametrize(
    "case",
    [
        DateRangeCase(
            "2026-06-27",
            "2026-06-28",
            (datetime(2026, 6, 27, tzinfo=UTC), datetime(2026, 6, 28, tzinfo=UTC)),
        ),
        DateRangeCase(
            "2026-06-27T18:00:00",
            "2026-06-28T18:00:00",
            (
                datetime(2026, 6, 27, 18, tzinfo=UTC),
                datetime(2026, 6, 28, 18, tzinfo=UTC),
            ),
        ),
    ],
)
def test_route_reads_naive_dates_as_utc(
    client: TestClient,
    factory: MarquiseFactory,
    case: DateRangeCase,
) -> None:
    """Date-only and naive datetimes reach the use case in UTC."""
    params = {"from": case.from_param, "to": case.to_param}
    response = client.get("/v1/cinemas/cin-date-contract/movies", params=params)
    assert response.status_code == 200
    request = factory.get_cinema_movies_use_case.execute.call_args.args[0]
    assert (request.start_date, request.end_date) == case.expected_range


def test_route_keeps_explicit_offsets(
    client: TestClient, factory: MarquiseFactory
) -> None:
    """Dates with an offset reach the use case with that offset."""
    montreal_summer = timezone(timedelta(hours=-4))
    params = {"from": "2026-06-27T18:00:00-04:00", "to": "2026-06-28T18:00:00-04:00"}
    response = client.get("/v1/cinemas/cin-date-contract/movies", params=params)
    assert response.status_code == 200
    request = factory.get_cinema_movies_use_case.execute.call_args.args[0]
    assert request.start_date == datetime(2026, 6, 27, 18, tzinfo=montreal_summer)
    assert request.end_date == datetime(2026, 6, 28, 18, tzinfo=montreal_summer)
    assert request.start_date.tzinfo == montreal_summer
    assert request.end_date.tzinfo == montreal_summer


def test_route_defaults_are_timezone_aware(
    client: TestClient, factory: MarquiseFactory
) -> None:
    """Omitted dates reach the use case as UTC dates one week apart."""
    response = client.get("/v1/cinemas/cin-date-contract/movies")
    assert response.status_code == 200
    request = factory.get_cinema_movies_use_case.execute.call_args.args[0]
    assert request.start_date.tzinfo == UTC
    assert request.end_date.tzinfo == UTC
    assert request.end_date - request.start_date == timedelta(days=7)
