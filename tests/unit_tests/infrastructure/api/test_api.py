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

from marquise.application.exceptions import (
    CinemaNotFoundError,
    MovieNotFoundError,
    ScreeningNotFoundError,
)
from marquise.application.use_cases.get_movie import GetMovieUseCase
from marquise.application.use_cases.list_movies import ListMoviesUseCase
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
    fake.get_cinema_screenings_use_case.execute = AsyncMock()
    fake.get_movie_use_case.execute = AsyncMock()
    fake.list_movies_use_case.execute = AsyncMock()
    fake.search_screenings_use_case.execute = AsyncMock()
    fake.get_screening_use_case.execute = AsyncMock()
    fake.get_movie_screenings_use_case.execute = AsyncMock()
    fake.get_cinema_movies_use_case.execute = AsyncMock()
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


def test_ready_returns_200_when_database_healthy(
    client: TestClient, container: MagicMock
) -> None:
    """The ready endpoint reports OK when the DB pool is healthy."""
    container.check_database_health = AsyncMock(return_value=True)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_503_when_database_unhealthy(
    client: TestClient, container: MagicMock
) -> None:
    """The ready endpoint reports 503 when the DB pool is unhealthy."""
    container.check_database_health = AsyncMock(return_value=False)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_ready_is_exempt_from_rate_limiting(
    monkeypatch: pytest.MonkeyPatch, container: MagicMock
) -> None:
    """/ready keeps responding even past the configured rate limit."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    container.check_database_health = AsyncMock(return_value=True)
    client = TestClient(create_app(container=container))

    responses = [client.get("/ready") for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)


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

    response = client.get("/v1/cinemas")

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

    response = client.get("/v1/cinemas", params={"name": "Cineplex"})

    assert response.status_code == 200
    container.cinema_controller.list.assert_awaited_once_with(
        name="Cineplex", page=1, size=50
    )


def test_get_cinema_screenings(client: TestClient, container: MagicMock) -> None:
    """GET /cinemas/{id}/screenings returns screenings in range."""
    container.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[
            SimpleNamespace(
                id="scr-1",
                movie_id="mov-1",
                movie_title="The Odyssey",
                cinema_id="cin-1",
                cinema_name="Cinema One",
                showtime="2026-06-27T19:30:00+00:00",
                ticket_url=None,
                room=None,
                language=None,
            )
        ],
        total=1,
    )

    response = client.get(
        "/v1/cinemas/cin-1/screenings",
        params={"from": "2026-06-27", "to": "2026-06-28"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["movie_title"] == "The Odyssey"
    assert body["items"][0]["cinema_id"] == "cin-1"
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

    response = client.get("/v1/cinemas", params={"page": 2, "size": 2})

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
    response = client.get("/v1/cinemas", params={"size": 101})

    assert response.status_code == 422


def test_get_cinema_screenings_pagination(
    client: TestClient, container: MagicMock
) -> None:
    """The router forwards page/size and reports the use case's total.

    The use case is mocked as already having applied pagination (as it does
    once page/size are pushed down to SQL), so this test verifies the
    router passes params through and reports ``total`` from the response
    rather than computing it from the page length.
    """
    container.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[
            SimpleNamespace(
                id="scr-3",
                movie_id="mov-1",
                movie_title="The Odyssey",
                cinema_id="cin-1",
                cinema_name="Cinema One",
                showtime="2026-06-27T19:30:00+00:00",
                ticket_url=None,
                room=None,
                language=None,
            ),
            SimpleNamespace(
                id="scr-4",
                movie_id="mov-1",
                movie_title="The Odyssey",
                cinema_id="cin-1",
                cinema_name="Cinema One",
                showtime="2026-06-27T21:30:00+00:00",
                ticket_url=None,
                room=None,
                language=None,
            ),
        ],
        total=5,
    )

    response = client.get(
        "/v1/cinemas/cin-1/screenings",
        params={"page": 2, "size": 2},
    )

    assert response.status_code == 200
    body = response.json()
    assert [s["id"] for s in body["items"]] == ["scr-3", "scr-4"]
    assert body["total"] == 5
    assert body["page"] == 2
    assert body["size"] == 2
    input_data = container.get_cinema_screenings_use_case.execute.call_args[0][0]
    assert input_data.page == 2
    assert input_data.size == 2


def test_get_cinema_screenings_not_found(
    client: TestClient, container: MagicMock
) -> None:
    """A missing cinema yields 404 with the standard error envelope."""
    container.get_cinema_screenings_use_case.execute.side_effect = CinemaNotFoundError(
        "nope"
    )

    response = client.get(
        "/v1/cinemas/missing/screenings",
        params={"from": "2026-06-27", "to": "2026-06-28"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body.pop("request_id")
    assert body == {"detail": "nope", "error_code": "not_found"}


def test_get_cinema_screenings_unexpected_value_error_returns_422_envelope(
    client: TestClient, container: MagicMock
) -> None:
    """A ValueError from the use case yields a 422 envelope."""
    container.get_cinema_screenings_use_case.execute.side_effect = ValueError(
        "bad input"
    )

    response = client.get("/v1/cinemas/cin-1/screenings")

    assert response.status_code == 422
    body = response.json()
    assert body.pop("request_id")
    assert body == {"detail": "bad input", "error_code": "invalid_input"}


def test_get_cinema_screenings_ignores_unsupported_query_params(
    client: TestClient, container: MagicMock
) -> None:
    """Filters beyond cinema scope aren't accepted — use GET /v1/screenings instead."""
    container.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
        total=0,
    )

    response = client.get(
        "/v1/cinemas/cin-1/screenings",
        params={"movie_id": "mov-1", "language": "V.O.", "from": "2026-06-27"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 0
    assert body["total"] == 0
    input_data = container.get_cinema_screenings_use_case.execute.call_args[0][0]
    assert input_data.cinema_id == "cin-1"
    assert not hasattr(input_data, "movie_id")
    assert not hasattr(input_data, "language")


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

    response = client.get("/v1/movies/mov-1")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "The Odyssey"
    assert body["release_year"] == 2026


def test_get_movie_not_found(client: TestClient, container: MagicMock) -> None:
    """A missing movie yields 404 with the standard error envelope."""
    container.get_movie_use_case.execute.side_effect = MovieNotFoundError("nope")

    response = client.get("/v1/movies/missing")

    assert response.status_code == 404
    body = response.json()
    assert body.pop("request_id")
    assert body == {"detail": "nope", "error_code": "not_found"}


def test_unhandled_exception_returns_generic_500(container: MagicMock) -> None:
    """An unexpected exception from a use case yields a generic 500 envelope.

    Uses a separate TestClient with raise_server_exceptions=False: the
    default client fixture re-raises the original exception after the
    handler's response is sent (Starlette's ServerErrorMiddleware behavior),
    which would make this test raise instead of asserting on the response.
    """
    container.get_movie_use_case.execute.side_effect = RuntimeError("db exploded")
    client = TestClient(create_app(container=container), raise_server_exceptions=False)

    response = client.get("/v1/movies/mov-1")

    assert response.status_code == 500
    body = response.json()
    assert body.pop("request_id")
    assert body == {
        "detail": "An unexpected RuntimeError occurred while processing the request.",
        "error_code": "internal_server_error",
    }


def test_list_movies(client: TestClient, container: MagicMock) -> None:
    """GET /movies returns the use case's movies."""
    container.list_movies_use_case.execute.return_value = SimpleNamespace(
        movies=[
            SimpleNamespace(
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
        ],
        total=1,
    )

    response = client.get("/v1/movies")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == "mov-1"
    assert body["items"][0]["title"] == "The Odyssey"
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["size"] == 50


def test_list_movies_delegates_to_use_case_with_title_filter(
    client: TestClient, container: MagicMock
) -> None:
    """GET /movies calls list_movies_use_case with the title filter and paging."""
    container.list_movies_use_case.execute.return_value = SimpleNamespace(
        movies=[], total=0
    )

    response = client.get("/v1/movies", params={"title": "Odyssey"})

    assert response.status_code == 200
    container.list_movies_use_case.execute.assert_awaited_once_with(
        ListMoviesUseCase.InputData(title="Odyssey", page=1, size=50)
    )


def test_list_movies_pagination(client: TestClient, container: MagicMock) -> None:
    """The router forwards page/size and reports the use case's total."""
    container.list_movies_use_case.execute.return_value = SimpleNamespace(
        movies=[
            SimpleNamespace(
                id="mov-1",
                title="Movie 1",
                release_year=None,
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
            ),
            SimpleNamespace(
                id="mov-2",
                title="Movie 2",
                release_year=None,
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
            ),
        ],
        total=5,
    )

    response = client.get("/v1/movies", params={"page": 2, "size": 2})

    assert response.status_code == 200
    body = response.json()
    assert [m["id"] for m in body["items"]] == ["mov-1", "mov-2"]
    assert body["total"] == 5
    assert body["page"] == 2
    assert body["size"] == 2
    container.list_movies_use_case.execute.assert_awaited_once_with(
        ListMoviesUseCase.InputData(title=None, page=2, size=2)
    )


def test_list_movies_size_out_of_range_is_rejected(
    client: TestClient, container: MagicMock
) -> None:
    """A size above the max page size is rejected with a 422."""
    response = client.get("/v1/movies", params={"size": 101})

    assert response.status_code == 422


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

    first = client.get("/v1/cinemas")
    second = client.get("/v1/cinemas")

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

    first = client.get("/v1/movies/mov-1")
    second = client.get("/v1/movies/mov-1")

    assert first.status_code == 200
    assert second.json() == first.json()
    container.get_movie_use_case.execute.assert_awaited_once()


def test_list_movies_is_cached(client: TestClient, container: MagicMock) -> None:
    """A second identical request reuses the cached result instead of re-executing."""
    container.list_movies_use_case.execute.return_value = SimpleNamespace(
        movies=[
            SimpleNamespace(
                id="mov-1",
                title="The Odyssey",
                release_year=None,
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
        ],
        total=1,
    )

    first = client.get("/v1/movies")
    second = client.get("/v1/movies")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    container.list_movies_use_case.execute.assert_awaited_once()


def test_get_cinema_screenings_is_cached(
    client: TestClient, container: MagicMock
) -> None:
    """A second request reuses the cached response."""
    container.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
        total=0,
    )

    first = client.get("/v1/cinemas/cin-1/screenings")
    second = client.get("/v1/cinemas/cin-1/screenings")

    assert first.status_code == 200
    assert second.json() == first.json()
    container.get_cinema_screenings_use_case.execute.assert_awaited_once()


def test_list_cinemas_cache_has_miss_header_on_first_request(
    client: TestClient, container: MagicMock
) -> None:
    """The first request for /cinemas has X-FastAPI-Cache: MISS header."""
    container.cinema_controller.list.return_value = SimpleNamespace(cinemas=[], total=0)

    response = client.get("/v1/cinemas")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "MISS"


def test_list_cinemas_cache_has_hit_header_on_repeat_request(
    client: TestClient, container: MagicMock
) -> None:
    """Repeat requests for /cinemas have X-FastAPI-Cache: HIT header."""
    container.cinema_controller.list.return_value = SimpleNamespace(cinemas=[], total=0)

    client.get("/v1/cinemas")
    response = client.get("/v1/cinemas")

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

    response = client.get("/v1/movies/mov-1")

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

    client.get("/v1/movies/mov-1")
    response = client.get("/v1/movies/mov-1")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "HIT"


def test_get_cinema_screenings_cache_has_miss_header_on_first_request(
    client: TestClient, container: MagicMock
) -> None:
    """The first screenings request has an X-FastAPI-Cache MISS header."""
    container.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
        total=0,
    )

    response = client.get("/v1/cinemas/cin-1/screenings")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "MISS"


def test_get_cinema_screenings_cache_has_hit_header_on_repeat_request(
    client: TestClient, container: MagicMock
) -> None:
    """Repeat requests for /cinemas/{id}/screenings have X-FastAPI-Cache: HIT header."""
    container.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
        total=0,
    )

    client.get("/v1/cinemas/cin-1/screenings")
    response = client.get("/v1/cinemas/cin-1/screenings")

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

    response1 = client.get("/v1/movies/mov-1")
    response2 = client.get("/v1/movies/mov-2")
    response1_again = client.get("/v1/movies/mov-1")

    assert response1.json()["id"] == "mov-1"
    assert response2.json()["id"] == "mov-2"
    assert response1_again.json() == response1.json()
    assert container.get_movie_use_case.execute.call_count == 2


def test_not_found_errors_are_not_cached(
    client: TestClient, container: MagicMock
) -> None:
    """404 responses are not cached; repeat requests re-execute the use case."""
    container.get_movie_use_case.execute.side_effect = MovieNotFoundError("not found")

    response1 = client.get("/v1/movies/missing")
    response2 = client.get("/v1/movies/missing")

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

    response1 = client.get("/v1/cinemas", params={"name": "Cineplex"})
    response2 = client.get("/v1/cinemas", params={"name": "Landmark"})
    response1_again = client.get("/v1/cinemas", params={"name": "Cineplex"})

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
    response = client.get("/v1/cinemas")
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
        "/v1/cinemas",
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
        "/v1/cinemas",
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
        "/v1/cinemas",
        headers={"Origin": "https://evil.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_rate_limit_headers_present_on_success(
    client: TestClient, container: MagicMock
) -> None:
    """A normal request under the limit reports rate-limit headers."""
    container.cinema_controller.list.return_value = SimpleNamespace(cinemas=[], total=0)

    response = client.get("/v1/cinemas")

    assert response.status_code == 200
    assert "x-ratelimit-limit" in response.headers
    assert "x-ratelimit-remaining" in response.headers
    assert "x-ratelimit-reset" in response.headers


def test_rate_limit_exceeded_returns_429(
    monkeypatch: pytest.MonkeyPatch, container: MagicMock
) -> None:
    """A client exceeding the configured rate limit gets a 429 with Retry-After."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    container.cinema_controller.list = AsyncMock(
        return_value=SimpleNamespace(cinemas=[], total=0)
    )
    client = TestClient(create_app(container=container))

    first = client.get("/v1/cinemas")
    second = client.get("/v1/cinemas")

    assert first.status_code == 200
    assert second.status_code == 429
    assert "retry-after" in second.headers
    assert "error" in second.json()


def test_health_is_exempt_from_rate_limiting(
    monkeypatch: pytest.MonkeyPatch, container: MagicMock
) -> None:
    """/health keeps responding 200 even past the configured rate limit."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    client = TestClient(create_app(container=container))

    responses = [client.get("/health") for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)


def test_rate_limit_is_configurable_via_env_var(
    monkeypatch: pytest.MonkeyPatch, container: MagicMock
) -> None:
    """A higher configured limit allows more requests before a 429."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "5/minute")
    container.cinema_controller.list = AsyncMock(
        return_value=SimpleNamespace(cinemas=[], total=0)
    )
    client = TestClient(create_app(container=container))

    responses = [client.get("/v1/cinemas") for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)
    assert client.get("/v1/cinemas").status_code == 429


def test_search_screenings(client: TestClient, container: MagicMock) -> None:
    """GET /screenings returns the use case's screenings."""
    container.search_screenings_use_case.execute.return_value = SimpleNamespace(
        screenings=[
            SimpleNamespace(
                id="scr-1",
                movie_id="mov-1",
                movie_title="The Odyssey",
                cinema_id="cin-1",
                cinema_name="Cinema One",
                showtime="2026-06-27T19:30:00+00:00",
                ticket_url=None,
                room=None,
                language=None,
            )
        ],
        total=1,
    )

    response = client.get("/v1/screenings")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["movie_title"] == "The Odyssey"
    assert body["items"][0]["cinema_id"] == "cin-1"


def test_search_screenings_delegates_to_use_case_with_filters(
    client: TestClient, container: MagicMock
) -> None:
    """GET /screenings forwards all query params to the use case."""
    container.search_screenings_use_case.execute.return_value = SimpleNamespace(
        screenings=[], total=0
    )

    response = client.get(
        "/v1/screenings",
        params={
            "movie": "Odyssey",
            "movie_id": "mov-1",
            "cinema_id": "cin-1",
            "language": "V.O.",
        },
    )

    assert response.status_code == 200
    input_data = container.search_screenings_use_case.execute.call_args[0][0]
    assert input_data.movie == "Odyssey"
    assert input_data.movie_id == "mov-1"
    assert input_data.cinema_id == "cin-1"
    assert input_data.language == "V.O."


def test_search_screenings_pagination(client: TestClient, container: MagicMock) -> None:
    """GET /screenings supports page/size pagination."""
    container.search_screenings_use_case.execute.return_value = SimpleNamespace(
        screenings=[
            SimpleNamespace(
                id="scr-1",
                movie_id="mov-1",
                movie_title="A",
                cinema_id="cin-1",
                cinema_name="Cinema One",
                showtime="2026-06-27T19:30:00+00:00",
                ticket_url=None,
                room=None,
                language=None,
            ),
            SimpleNamespace(
                id="scr-2",
                movie_id="mov-2",
                movie_title="B",
                cinema_id="cin-2",
                cinema_name="Cinema Two",
                showtime="2026-06-27T20:30:00+00:00",
                ticket_url=None,
                room=None,
                language=None,
            ),
        ],
        total=10,
    )

    response = client.get("/v1/screenings", params={"page": 2, "size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 10
    assert body["page"] == 2
    assert body["size"] == 2
    container.search_screenings_use_case.execute.assert_awaited_once()


def test_search_screenings_size_out_of_range_is_rejected(
    client: TestClient,
) -> None:
    """A size above the max page size is rejected with a 422."""
    response = client.get("/v1/screenings", params={"size": 101})

    assert response.status_code == 422


def test_search_screenings_invalid_range_returns_422_envelope(
    client: TestClient, container: MagicMock
) -> None:
    """An invalid date range from the use case is surfaced as a 422 envelope."""
    container.search_screenings_use_case.execute.side_effect = ValueError(
        "start_date must not be after end_date"
    )

    response = client.get(
        "/v1/screenings",
        params={"from": "2026-06-28T00:00:00Z", "to": "2026-06-27T00:00:00Z"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "invalid_input"


def test_search_screenings_is_not_cached(
    client: TestClient, container: MagicMock
) -> None:
    """Repeated identical requests to /screenings are not served from cache."""
    container.search_screenings_use_case.execute.return_value = SimpleNamespace(
        screenings=[], total=0
    )

    first = client.get("/v1/screenings")
    second = client.get("/v1/screenings")

    assert first.status_code == 200
    assert second.status_code == 200
    assert container.search_screenings_use_case.execute.await_count == 2


def test_get_screening(client: TestClient, container: MagicMock) -> None:
    """GET /screenings/{id} returns the screening."""
    container.get_screening_use_case.execute.return_value = SimpleNamespace(
        id="scr-1",
        movie_id="mov-1",
        movie_title="The Odyssey",
        cinema_id="cin-1",
        cinema_name="Cinema One",
        showtime="2026-06-27T19:30:00+00:00",
        ticket_url=None,
        room=None,
        language=None,
    )

    response = client.get("/v1/screenings/scr-1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "scr-1"
    assert body["movie_title"] == "The Odyssey"
    assert body["cinema_id"] == "cin-1"


def test_get_screening_not_found(client: TestClient, container: MagicMock) -> None:
    """GET /screenings/{id} returns a 404 envelope for a missing screening."""
    container.get_screening_use_case.execute.side_effect = ScreeningNotFoundError(
        "A screening with ID 'missing' was not found"
    )

    response = client.get("/v1/screenings/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "not_found"


def test_get_movie_screenings(client: TestClient, container: MagicMock) -> None:
    """GET /movies/{id}/screenings returns all of the movie's screenings."""
    container.get_movie_screenings_use_case.execute.return_value = SimpleNamespace(
        movie_id="mov-1",
        movie_title="The Odyssey",
        screenings=[
            SimpleNamespace(
                id="scr-1",
                movie_id="mov-1",
                movie_title="The Odyssey",
                cinema_id="cin-1",
                cinema_name="Cinema One",
                showtime="2026-06-27T19:30:00+00:00",
                ticket_url=None,
                room=None,
                language=None,
            )
        ],
        total=1,
    )

    response = client.get("/v1/movies/mov-1/screenings")

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["movie_title"] == "The Odyssey"
    assert body["items"][0]["cinema_id"] == "cin-1"
    assert body["total"] == 1


def test_get_movie_screenings_ignores_unsupported_query_params(
    client: TestClient, container: MagicMock
) -> None:
    """Filters beyond movie scope aren't accepted — use GET /v1/screenings instead."""
    container.get_movie_screenings_use_case.execute.return_value = SimpleNamespace(
        movie_id="mov-1", movie_title="The Odyssey", screenings=[], total=0
    )

    response = client.get(
        "/v1/movies/mov-1/screenings",
        params={"cinema_id": "cin-1", "language": "V.O.", "from": "2026-06-27"},
    )

    assert response.status_code == 200
    input_data = container.get_movie_screenings_use_case.execute.call_args[0][0]
    assert input_data.movie_id == "mov-1"
    assert not hasattr(input_data, "cinema_id")
    assert not hasattr(input_data, "language")


def test_get_movie_screenings_not_found(
    client: TestClient, container: MagicMock
) -> None:
    """GET /movies/{id}/screenings returns a 404 envelope for a missing movie."""
    container.get_movie_screenings_use_case.execute.side_effect = MovieNotFoundError(
        "A movie with ID 'missing' was not found"
    )

    response = client.get("/v1/movies/missing/screenings")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "not_found"


def test_get_cinema_movies(client: TestClient, container: MagicMock) -> None:
    """GET /cinemas/{id}/movies returns the cinema's distinct movies."""
    container.get_cinema_movies_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        movies=[
            SimpleNamespace(
                id="mov-1",
                title="The Odyssey",
                release_year=None,
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
        ],
        total=1,
    )

    response = client.get(
        "/v1/cinemas/cin-1/movies",
        params={"from": "2026-06-27", "to": "2026-06-28"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["title"] == "The Odyssey"
    assert body["total"] == 1


def test_get_cinema_movies_not_found(client: TestClient, container: MagicMock) -> None:
    """GET /cinemas/{id}/movies returns a 404 envelope for an unknown cinema."""
    container.get_cinema_movies_use_case.execute.side_effect = CinemaNotFoundError(
        "A cinema with ID 'missing' was not found"
    )

    response = client.get("/v1/cinemas/missing/movies")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "not_found"


def test_get_cinema_movies_pagination(client: TestClient, container: MagicMock) -> None:
    """The router forwards page/size and reports the use case's total."""
    container.get_cinema_movies_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        movies=[],
        total=5,
    )

    response = client.get("/v1/cinemas/cin-1/movies", params={"page": 2, "size": 2})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 5
    assert body["page"] == 2
    assert body["size"] == 2
