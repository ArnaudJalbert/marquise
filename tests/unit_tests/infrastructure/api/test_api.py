"""Tests for the read-only FastAPI application.

The DI container is replaced with a MagicMock whose use cases are stubbed,
so these tests touch no database.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from marquise.application.exceptions import CinemaNotFoundError, MovieNotFoundError
from marquise.infrastructure.api.app import create_app


@pytest.fixture
def container() -> MagicMock:
    """Provide a fake DI container with stubbable read use cases."""
    fake = MagicMock()
    fake.list_cinemas_use_case.execute = AsyncMock()
    fake.get_cinema_showtimes_use_case.execute = AsyncMock()
    fake.get_movie_use_case.execute = AsyncMock()
    return fake


@pytest.fixture
def client(container: MagicMock) -> TestClient:
    """Provide a TestClient backed by the fake container."""
    return TestClient(create_app(container=container))


def test_health(client: TestClient) -> None:
    """The health endpoint reports OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_cinemas(client: TestClient, container: MagicMock) -> None:
    """GET /cinemas returns the use case's cinemas."""
    container.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[
            SimpleNamespace(
                id="cin-1",
                name="Cinema One",
                address="123 St",
                city="Montréal",
                website=None,
            )
        ]
    )

    response = client.get("/cinemas")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "cin-1"
    assert body[0]["name"] == "Cinema One"


def test_get_cinema_showtimes(client: TestClient, container: MagicMock) -> None:
    """GET /cinemas/{id}/showtimes returns screenings in range."""
    container.get_cinema_showtimes_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[
            SimpleNamespace(
                id="scr-1",
                movie_id="mov-1",
                movie_title="The Odyssey",
                showtime="2026-06-27T19:30:00+00:00",
                ticket_url=None,
                room=None,
                language=None,
            )
        ],
    )

    response = client.get(
        "/cinemas/cin-1/showtimes",
        params={"from": "2026-06-27", "to": "2026-06-28"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["cinema_name"] == "Cinema One"
    assert body["screenings"][0]["movie_title"] == "The Odyssey"


def test_get_cinema_showtimes_not_found(
    client: TestClient, container: MagicMock
) -> None:
    """A missing cinema yields 404."""
    container.get_cinema_showtimes_use_case.execute.side_effect = CinemaNotFoundError(
        "nope"
    )

    response = client.get(
        "/cinemas/missing/showtimes",
        params={"from": "2026-06-27", "to": "2026-06-28"},
    )

    assert response.status_code == 404


def test_get_cinema_showtimes_requires_dates(client: TestClient) -> None:
    """Missing from/to query params yield a 422 validation error."""
    response = client.get("/cinemas/cin-1/showtimes")
    assert response.status_code == 422


def test_get_movie(client: TestClient, container: MagicMock) -> None:
    """GET /movies/{id} returns the movie."""
    container.get_movie_use_case.execute.return_value = SimpleNamespace(
        id="mov-1",
        title="The Odyssey",
        release_year=2026,
        directors=("Jane Director",),
        cast=None,
        duration_minutes=120,
        description=None,
        poster_url=None,
        trailer_url=None,
        genres=None,
        original_title=None,
        rating=None,
        origin_countries=None,
    )

    response = client.get("/movies/mov-1")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "The Odyssey"
    assert body["release_year"] == 2026


def test_get_movie_not_found(client: TestClient, container: MagicMock) -> None:
    """A missing movie yields 404."""
    container.get_movie_use_case.execute.side_effect = MovieNotFoundError("nope")

    response = client.get("/movies/missing")

    assert response.status_code == 404
