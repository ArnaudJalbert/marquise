"""The cinema movies route supplies timezone-aware use-case dates."""

from datetime import UTC, timedelta, timezone
from unittest.mock import create_autospec

import pytest
from fastapi.testclient import TestClient

from marquise import GetCinemaMoviesUseCase, MarquiseFactory
from marquise_api.app import create_app


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
    "date_case",
    [("", UTC), ("T18:00:00", UTC), ("T18:00:00-04:00", timezone(timedelta(hours=-4)))],
)
def test_route_preserves_date_inputs_with_explicit_timezone(
    client: TestClient, factory: MarquiseFactory, date_case: tuple[str, timezone]
) -> None:
    """Date-only and naive dates assume UTC; explicit offsets stay intact."""
    date_suffix, expected_zone = date_case
    params = {"from": f"2026-06-27{date_suffix}", "to": f"2026-06-28{date_suffix}"}
    response = client.get("/v1/cinemas/cin-date-contract/movies", params=params)
    assert response.status_code == 200
    request = factory.get_cinema_movies_use_case.execute.call_args.args[0]
    assert request.start_date.tzinfo == expected_zone
    assert request.end_date.tzinfo == expected_zone
    assert request.start_date.hour == (18 if date_suffix else 0)
    assert request.end_date.hour == (18 if date_suffix else 0)


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
