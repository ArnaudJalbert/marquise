"""Tests for the read-only FastAPI application.

The DI container is replaced with a MagicMock whose use cases are stubbed,
so these tests touch no database.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from fastapi_cache.backends.inmemory import InMemoryBackend

from marquise.application.exceptions import CinemaNotFoundError, MovieNotFoundError
from marquise.application.use_cases.get_cinema_showtimes import (
    GetCinemaShowtimesUseCase,
)
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.infrastructure.api.app import CACHE_PREFIX, create_app


@pytest.fixture(autouse=True)
def _clear_response_cache() -> None:
    """Clear cached responses after each test.

    InMemoryBackend stores its data on a class attribute shared by every
    instance, so repeated create_app() calls across tests would otherwise
    leak cached responses between them.
    """
    yield
    asyncio.run(InMemoryBackend().clear(namespace=CACHE_PREFIX))


@pytest.fixture
def container() -> MagicMock:
    """Provide a fake DI container with stubbable read use cases."""
    fake = MagicMock()
    fake.cinema_controller.list = AsyncMock()
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
    container.cinema_controller.list.return_value = SimpleNamespace(
        cinemas=[
            SimpleNamespace(
                id="cin-1",
                name="Cinema One",
                address="123 St",
                city="Montréal",
                website=None,
            )
        ],
        total=1,
    )

    response = client.get("/cinemas")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == "cin-1"
    assert body["items"][0]["name"] == "Cinema One"
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["size"] == 50


def test_list_cinemas_delegates_to_cinema_controller(
    client: TestClient, container: MagicMock
) -> None:
    """GET /cinemas calls cinema_controller.list(), not the use case directly."""
    container.cinema_controller.list.return_value = SimpleNamespace(cinemas=[], total=0)

    response = client.get("/cinemas", params={"name": "Cineplex"})

    assert response.status_code == 200
    container.cinema_controller.list.assert_awaited_once_with(
        name="Cineplex", page=1, size=50
    )


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
        total=1,
    )

    response = client.get(
        "/cinemas/cin-1/showtimes",
        params={"from": "2026-06-27", "to": "2026-06-28"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["movie_title"] == "The Odyssey"
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["size"] == 50


def test_list_cinemas_pagination(client: TestClient, container: MagicMock) -> None:
    """The router forwards page/size and reports the controller's total.

    The controller is mocked as already having applied pagination (as it
    does once page/size are pushed down to SQL), so this test verifies
    the router passes params through and reports ``total`` from the
    response rather than computing it from the page length.
    """
    container.cinema_controller.list.return_value = SimpleNamespace(
        cinemas=[
            SimpleNamespace(
                id="cin-1", name="Cinema 1", address=None, city=None, website=None
            ),
            SimpleNamespace(
                id="cin-2", name="Cinema 2", address=None, city=None, website=None
            ),
        ],
        total=5,
    )

    response = client.get("/cinemas", params={"page": 2, "size": 2})

    assert response.status_code == 200
    body = response.json()
    assert [c["id"] for c in body["items"]] == ["cin-1", "cin-2"]
    assert body["total"] == 5
    assert body["page"] == 2
    assert body["size"] == 2
    container.cinema_controller.list.assert_awaited_once_with(name=None, page=2, size=2)


def test_list_cinemas_size_out_of_range_is_rejected(
    client: TestClient, container: MagicMock
) -> None:
    """A size above the max page size is rejected with a 422."""
    response = client.get("/cinemas", params={"size": 101})

    assert response.status_code == 422


def test_get_cinema_showtimes_pagination(
    client: TestClient, container: MagicMock
) -> None:
    """The router forwards page/size and reports the use case's total.

    The use case is mocked as already having applied pagination (as it does
    once page/size are pushed down to SQL), so this test verifies the
    router passes params through and reports ``total`` from the response
    rather than computing it from the page length.
    """
    container.get_cinema_showtimes_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[
            SimpleNamespace(
                id="scr-3",
                movie_id="mov-1",
                movie_title="The Odyssey",
                showtime="2026-06-27T19:30:00+00:00",
                ticket_url=None,
                room=None,
                language=None,
            ),
            SimpleNamespace(
                id="scr-4",
                movie_id="mov-1",
                movie_title="The Odyssey",
                showtime="2026-06-27T21:30:00+00:00",
                ticket_url=None,
                room=None,
                language=None,
            ),
        ],
        total=5,
    )

    response = client.get(
        "/cinemas/cin-1/showtimes",
        params={"from": "2026-06-27", "to": "2026-06-28", "page": 2, "size": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert [s["id"] for s in body["items"]] == ["scr-3", "scr-4"]
    assert body["total"] == 5
    assert body["page"] == 2
    assert body["size"] == 2
    input_data = container.get_cinema_showtimes_use_case.execute.call_args[0][0]
    assert input_data.page == 2
    assert input_data.size == 2


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
        total=0,
    )

    response = client.get("/cinemas/cin-1/showtimes")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 0
    assert body["total"] == 0
    container.get_cinema_showtimes_use_case.execute.assert_awaited_once()


def test_get_cinema_showtimes_default_dates_are_utc_aware(
    client: TestClient, container: MagicMock
) -> None:
    """Omitting from/to resolves a timezone-aware UTC range, not naive local time."""
    captured: list[GetCinemaShowtimesUseCase.InputData] = []

    async def fake_execute(
        input_data: GetCinemaShowtimesUseCase.InputData,
    ) -> SimpleNamespace:
        captured.append(input_data)
        return SimpleNamespace(
            cinema_id="cin-1", cinema_name="Cinema One", screenings=[], total=0
        )

    container.get_cinema_showtimes_use_case.execute.side_effect = fake_execute

    response = client.get("/cinemas/cin-1/showtimes")

    assert response.status_code == 200
    assert captured[0].start_date.tzinfo is not None
    assert captured[0].end_date.tzinfo is not None


def test_get_cinema_showtimes_default_dates_are_cached_within_the_same_day(
    client: TestClient, container: MagicMock
) -> None:
    """Repeat requests omitting from/to on the same day share one cache entry.

    The default date range is resolved via a dependency (before the cached
    endpoint runs), so the cache key reflects the resolved dates rather than
    the raw None query params — otherwise every omitted-date request would
    collide on a single entry frozen at whichever moment first populated it.
    """
    container.get_cinema_showtimes_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
        total=0,
    )

    first = client.get("/cinemas/cin-1/showtimes")
    second = client.get("/cinemas/cin-1/showtimes")

    assert first.headers.get("X-FastAPI-Cache") == "MISS"
    assert second.headers.get("X-FastAPI-Cache") == "HIT"
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
    container.cinema_controller.list.return_value = SimpleNamespace(
        cinemas=[
            SimpleNamespace(
                id="cin-1",
                name="Cinema One",
                address=None,
                city=None,
                website=None,
            )
        ],
        total=1,
    )

    first = client.get("/cinemas")
    second = client.get("/cinemas")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    container.cinema_controller.list.assert_awaited_once()


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
        total=0,
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
    container.cinema_controller.list.return_value = SimpleNamespace(cinemas=[], total=0)

    response = client.get("/cinemas")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "MISS"


def test_list_cinemas_cache_has_hit_header_on_repeat_request(
    client: TestClient, container: MagicMock
) -> None:
    """Repeat requests for /cinemas have X-FastAPI-Cache: HIT header."""
    container.cinema_controller.list.return_value = SimpleNamespace(cinemas=[], total=0)

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
        total=0,
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
        total=0,
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
        total=0,
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

    def mock_list(
        name: str | None, page: int = 1, size: int | None = None
    ) -> SimpleNamespace:
        if name == "Cineplex":
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
        return SimpleNamespace(cinemas=cinemas, total=len(cinemas))

    container.cinema_controller.list.side_effect = mock_list

    response1 = client.get("/cinemas", params={"name": "Cineplex"})
    response2 = client.get("/cinemas", params={"name": "Landmark"})
    response1_again = client.get("/cinemas", params={"name": "Cineplex"})

    assert response1.json()["items"][0]["name"] == "Cineplex Downtown"
    assert response2.json()["items"][0]["name"] == "Landmark Cinemas"
    assert response1_again.json() == response1.json()
    assert response1_again.headers.get("X-FastAPI-Cache") == "HIT"
    assert container.cinema_controller.list.call_count == 2


def test_cors_not_configured_by_default(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CORS headers are absent when MARQUISE_API_CORS_ORIGINS is not set.

    Creating the client before clearing the env var means it was built with
    the default (empty) origins, so no CORSMiddleware was installed.
    """
    monkeypatch.delenv("MARQUISE_API_CORS_ORIGINS", raising=False)
    response = client.get("/cinemas")
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_headers_present_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """CORS headers are returned when MARQUISE_API_CORS_ORIGINS is set."""
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "http://localhost:3000")
    container = MagicMock()
    container.cinema_controller.list = AsyncMock(
        return_value=SimpleNamespace(cinemas=[], total=0)
    )
    client = TestClient(create_app(container=container))

    response = client.get(
        "/cinemas",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_preflight_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """OPTIONS preflight requests return CORS headers when configured."""
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "http://localhost:3000")
    container = MagicMock()
    container.cinema_controller.list = AsyncMock(
        return_value=SimpleNamespace(cinemas=[], total=0)
    )
    client = TestClient(create_app(container=container))

    response = client.options(
        "/cinemas",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-methods"] == "GET"


def test_cors_origin_not_allowed_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Requests from an origin not in the allowed list get no CORS headers."""
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "http://localhost:3000")
    container = MagicMock()
    container.cinema_controller.list = AsyncMock(
        return_value=SimpleNamespace(cinemas=[], total=0)
    )
    client = TestClient(create_app(container=container))

    response = client.get(
        "/cinemas",
        headers={"Origin": "https://evil.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
