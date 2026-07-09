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
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.list_cinemas import ListCinemasUseCase
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


def test_get_cinema_showtimes_with_default_dates(
    client: TestClient, container: MagicMock
) -> None:
    """Omitting from/to query params uses defaults (today + 7 days)."""
    container.get_cinema_showtimes_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
    )

    response = client.get("/cinemas/cin-1/showtimes")

    assert response.status_code == 200
    body = response.json()
    assert body["cinema_id"] == "cin-1"
    assert body["cinema_name"] == "Cinema One"
    container.get_cinema_showtimes_use_case.execute.assert_awaited_once()


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


def test_list_cinemas_is_cached(client: TestClient, container: MagicMock) -> None:
    """A second identical request reuses the cached result instead of re-executing."""
    container.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[
            SimpleNamespace(
                id="cin-1",
                name="Cinema One",
                address=None,
                city=None,
                website=None,
            )
        ]
    )

    first = client.get("/cinemas")
    second = client.get("/cinemas")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    container.list_cinemas_use_case.execute.assert_awaited_once()


def test_get_movie_is_cached(client: TestClient, container: MagicMock) -> None:
    """A second request for the same movie reuses the cached response."""
    container.get_movie_use_case.execute.return_value = SimpleNamespace(
        id="mov-1",
        title="The Odyssey",
        release_year=2026,
        directors=None,
        cast=None,
        duration_minutes=None,
        description=None,
        poster_url=None,
        trailer_url=None,
        genres=None,
        original_title=None,
        rating=None,
        origin_countries=None,
    )

    first = client.get("/movies/mov-1")
    second = client.get("/movies/mov-1")

    assert first.status_code == 200
    assert second.json() == first.json()
    container.get_movie_use_case.execute.assert_awaited_once()


def test_get_cinema_showtimes_is_cached(
    client: TestClient, container: MagicMock
) -> None:
    """A second request with the same range reuses the cached response."""
    container.get_cinema_showtimes_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
    )
    params = {"from": "2026-06-27", "to": "2026-06-28"}

    first = client.get("/cinemas/cin-1/showtimes", params=params)
    second = client.get("/cinemas/cin-1/showtimes", params=params)

    assert first.status_code == 200
    assert second.json() == first.json()
    container.get_cinema_showtimes_use_case.execute.assert_awaited_once()


def test_list_cinemas_cache_has_miss_header_on_first_request(
    client: TestClient, container: MagicMock
) -> None:
    """The first request for /cinemas has X-FastAPI-Cache: MISS header."""
    container.list_cinemas_use_case.execute.return_value = SimpleNamespace(cinemas=[])

    response = client.get("/cinemas")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "MISS"


def test_list_cinemas_cache_has_hit_header_on_repeat_request(
    client: TestClient, container: MagicMock
) -> None:
    """Repeat requests for /cinemas have X-FastAPI-Cache: HIT header."""
    container.list_cinemas_use_case.execute.return_value = SimpleNamespace(cinemas=[])

    client.get("/cinemas")
    response = client.get("/cinemas")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "HIT"


def test_get_movie_cache_has_miss_header_on_first_request(
    client: TestClient, container: MagicMock
) -> None:
    """The first request for /movies/{id} has X-FastAPI-Cache: MISS header."""
    container.get_movie_use_case.execute.return_value = SimpleNamespace(
        id="mov-1",
        title="Test Movie",
        release_year=2026,
        directors=None,
        cast=None,
        duration_minutes=None,
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
    assert response.headers.get("X-FastAPI-Cache") == "MISS"


def test_get_movie_cache_has_hit_header_on_repeat_request(
    client: TestClient, container: MagicMock
) -> None:
    """Repeat requests for /movies/{id} have X-FastAPI-Cache: HIT header."""
    container.get_movie_use_case.execute.return_value = SimpleNamespace(
        id="mov-1",
        title="Test Movie",
        release_year=2026,
        directors=None,
        cast=None,
        duration_minutes=None,
        description=None,
        poster_url=None,
        trailer_url=None,
        genres=None,
        original_title=None,
        rating=None,
        origin_countries=None,
    )

    client.get("/movies/mov-1")
    response = client.get("/movies/mov-1")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "HIT"


def test_get_cinema_showtimes_cache_has_miss_header_on_first_request(
    client: TestClient, container: MagicMock
) -> None:
    """The first showtimes request has an X-FastAPI-Cache MISS header."""
    container.get_cinema_showtimes_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
    )
    params = {"from": "2026-06-27", "to": "2026-06-28"}

    response = client.get("/cinemas/cin-1/showtimes", params=params)

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "MISS"


def test_get_cinema_showtimes_cache_has_hit_header_on_repeat_request(
    client: TestClient, container: MagicMock
) -> None:
    """Repeat requests for /cinemas/{id}/showtimes have X-FastAPI-Cache: HIT header."""
    container.get_cinema_showtimes_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
    )
    params = {"from": "2026-06-27", "to": "2026-06-28"}

    client.get("/cinemas/cin-1/showtimes", params=params)
    response = client.get("/cinemas/cin-1/showtimes", params=params)

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "HIT"


def test_different_movies_have_separate_cache_entries(
    client: TestClient, container: MagicMock
) -> None:
    """Requests for different movie IDs have separate cache entries."""

    def mock_execute(input_data: GetMovieUseCase.InputData) -> SimpleNamespace:
        return SimpleNamespace(
            id=input_data.movie_id,
            title=f"Movie {input_data.movie_id}",
            release_year=2026,
            directors=None,
            cast=None,
            duration_minutes=None,
            description=None,
            poster_url=None,
            trailer_url=None,
            genres=None,
            original_title=None,
            rating=None,
            origin_countries=None,
        )

    container.get_movie_use_case.execute.side_effect = mock_execute

    response1 = client.get("/movies/mov-1")
    response2 = client.get("/movies/mov-2")
    response1_again = client.get("/movies/mov-1")

    assert response1.json()["id"] == "mov-1"
    assert response2.json()["id"] == "mov-2"
    assert response1_again.json() == response1.json()
    assert container.get_movie_use_case.execute.call_count == 2


def test_different_date_ranges_have_separate_cache_entries(
    client: TestClient, container: MagicMock
) -> None:
    """Different date ranges for the same cinema create separate cache entries."""
    container.get_cinema_showtimes_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
    )

    params1 = {"from": "2026-06-27", "to": "2026-06-28"}
    params2 = {"from": "2026-06-29", "to": "2026-06-30"}

    response1 = client.get("/cinemas/cin-1/showtimes", params=params1)
    response2 = client.get("/cinemas/cin-1/showtimes", params=params2)
    response1_again = client.get("/cinemas/cin-1/showtimes", params=params1)

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1_again.status_code == 200
    assert response1_again.headers.get("X-FastAPI-Cache") == "HIT"
    assert container.get_cinema_showtimes_use_case.execute.call_count == 2


def test_not_found_errors_are_not_cached(
    client: TestClient, container: MagicMock
) -> None:
    """404 responses are not cached; repeat requests re-execute the use case."""
    container.get_movie_use_case.execute.side_effect = MovieNotFoundError("not found")

    response1 = client.get("/movies/missing")
    response2 = client.get("/movies/missing")

    assert response1.status_code == 404
    assert response2.status_code == 404
    assert container.get_movie_use_case.execute.call_count == 2


def test_list_cinemas_with_name_filter_creates_separate_cache_entry(
    client: TestClient, container: MagicMock
) -> None:
    """Query parameter differences create separate cache entries."""

    def mock_execute(input_data: ListCinemasUseCase.InputData) -> SimpleNamespace:
        if input_data.name == "Cineplex":
            cinemas = [
                SimpleNamespace(
                    id="cin-1",
                    name="Cineplex Downtown",
                    address=None,
                    city=None,
                    website=None,
                )
            ]
        else:
            cinemas = [
                SimpleNamespace(
                    id="cin-2",
                    name="Landmark Cinemas",
                    address=None,
                    city=None,
                    website=None,
                )
            ]
        return SimpleNamespace(cinemas=cinemas)

    container.list_cinemas_use_case.execute.side_effect = mock_execute

    response1 = client.get("/cinemas", params={"name": "Cineplex"})
    response2 = client.get("/cinemas", params={"name": "Landmark"})
    response1_again = client.get("/cinemas", params={"name": "Cineplex"})

    assert response1.json()[0]["name"] == "Cineplex Downtown"
    assert response2.json()[0]["name"] == "Landmark Cinemas"
    assert response1_again.json() == response1.json()
    assert response1_again.headers.get("X-FastAPI-Cache") == "HIT"
    assert container.list_cinemas_use_case.execute.call_count == 2
