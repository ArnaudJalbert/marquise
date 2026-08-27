"""Tests for the read-only FastAPI application.

The DI container is replaced with a MagicMock whose use cases are stubbed,
so these tests touch no database.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient
from fastapi_cache.backends.inmemory import InMemoryBackend

from marquise import (
    CinemaNotFoundError,
    GetCinemaMoviesUseCase,
    GetCinemaScreeningsUseCase,
    GetCinemaUseCase,
    GetMovieScreeningsUseCase,
    GetMovieUseCase,
    GetScreeningUseCase,
    ListCinemasUseCase,
    ListMoviesUseCase,
    MarquiseFactory,
    MovieNotFoundError,
    ScreeningNotFoundError,
    SearchScreeningsUseCase,
)
from marquise_api.app import CACHE_PREFIX, create_app


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
def factory() -> MagicMock:
    """Provide fake factory with autospecced read use cases."""
    fake = create_autospec(MarquiseFactory, instance=True)
    fake.list_cinemas_use_case = create_autospec(ListCinemasUseCase, instance=True)
    fake.get_cinema_use_case = create_autospec(GetCinemaUseCase, instance=True)
    fake.get_cinema_screenings_use_case = create_autospec(
        GetCinemaScreeningsUseCase, instance=True
    )
    fake.get_cinema_movies_use_case = create_autospec(
        GetCinemaMoviesUseCase, instance=True
    )
    fake.list_movies_use_case = create_autospec(ListMoviesUseCase, instance=True)
    fake.get_movie_use_case = create_autospec(GetMovieUseCase, instance=True)
    fake.get_movie_screenings_use_case = create_autospec(
        GetMovieScreeningsUseCase, instance=True
    )
    fake.search_screenings_use_case = create_autospec(
        SearchScreeningsUseCase, instance=True
    )
    fake.get_screening_use_case = create_autospec(GetScreeningUseCase, instance=True)
    return fake


@pytest.fixture
def client(factory: MagicMock) -> TestClient:
    """Provide a TestClient backed by the fake container."""
    return TestClient(create_app(factory=factory))


def test_health(client: TestClient) -> None:
    """The health endpoint reports OK."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_200_when_database_healthy(
    client: TestClient, factory: MagicMock
) -> None:
    """The ready endpoint reports OK when the DB pool is healthy."""
    factory.check_database_health = AsyncMock(return_value=True)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_503_when_database_unhealthy(
    client: TestClient, factory: MagicMock
) -> None:
    """The ready endpoint reports 503 when the DB pool is unhealthy."""
    factory.check_database_health = AsyncMock(return_value=False)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_ready_is_exempt_from_rate_limiting(
    monkeypatch: pytest.MonkeyPatch, factory: MagicMock
) -> None:
    """/ready keeps responding even past the configured rate limit."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    factory.check_database_health = AsyncMock(return_value=True)
    client = TestClient(create_app(factory=factory))

    responses = [client.get("/ready") for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)


def test_list_cinemas(client: TestClient, factory: MagicMock) -> None:
    """GET /cinemas returns the use case's cinemas."""
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
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


def test_list_cinemas_executes_use_case_dto(
    client: TestClient, factory: MagicMock
) -> None:
    """GET /cinemas executes list use case with filter and pagination DTO."""
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )

    response = client.get("/v1/cinemas", params={"name": "Cineplex"})

    assert response.status_code == 200
    factory.list_cinemas_use_case.execute.assert_awaited_once_with(
        ListCinemasUseCase.InputData(name="Cineplex", page=1, size=50)
    )


def test_get_cinema_screenings(client: TestClient, factory: MagicMock) -> None:
    """GET /cinemas/{id}/screenings returns screenings in range."""
    factory.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
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


def test_list_cinemas_pagination(client: TestClient, factory: MagicMock) -> None:
    """The router forwards page/size and reports use case total.

    Use case mock already applied pagination, so this test verifies
    the router passes params through and reports ``total`` from the
    response rather than computing it from the page length.
    """
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
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
    factory.list_cinemas_use_case.execute.assert_awaited_once_with(
        ListCinemasUseCase.InputData(name=None, page=2, size=2)
    )


def test_list_cinemas_size_out_of_range_is_rejected(
    client: TestClient, factory: MagicMock
) -> None:
    """A size above the max page size is rejected with a 422."""
    response = client.get("/v1/cinemas", params={"size": 101})

    assert response.status_code == 422


def test_get_cinema(client: TestClient, factory: MagicMock) -> None:
    """GET /cinemas/{id} returns the cinema."""
    factory.get_cinema_use_case.execute.return_value = SimpleNamespace(
        id="cin-1",
        name="Cinema One",
        address="123 Rue Sainte-Catherine",
        city="Montréal",
        website=None,
    )

    response = client.get("/v1/cinemas/cin-1")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "cin-1"
    assert body["name"] == "Cinema One"
    assert body["address"] == "123 Rue Sainte-Catherine"
    assert body["city"] == "Montréal"
    assert body["website"] is None
    factory.get_cinema_use_case.execute.assert_awaited_once_with(
        GetCinemaUseCase.InputData(cinema_id="cin-1")
    )


def test_get_cinema_not_found(client: TestClient, factory: MagicMock) -> None:
    """A missing cinema yields 404 with the standard error envelope."""
    factory.get_cinema_use_case.execute.side_effect = CinemaNotFoundError("nope")

    response = client.get("/v1/cinemas/missing")

    assert response.status_code == 404
    body = response.json()
    assert body.pop("request_id")
    assert body == {"detail": "nope", "error_code": "not_found"}


def test_get_cinema_is_cached(client: TestClient, factory: MagicMock) -> None:
    """A second request for the same cinema reuses the cached response."""
    factory.get_cinema_use_case.execute.return_value = SimpleNamespace(
        id="cin-1",
        name="Cinema One",
        address=None,
        city=None,
        website=None,
    )

    first = client.get("/v1/cinemas/cin-1")
    second = client.get("/v1/cinemas/cin-1")

    assert first.status_code == 200
    assert second.json() == first.json()
    factory.get_cinema_use_case.execute.assert_awaited_once()


def test_get_cinema_cache_has_miss_header_on_first_request(
    client: TestClient, factory: MagicMock
) -> None:
    """The first request for /cinemas/{id} has X-FastAPI-Cache: MISS header."""
    factory.get_cinema_use_case.execute.return_value = SimpleNamespace(
        id="cin-1",
        name="Test Cinema",
        address=None,
        city=None,
        website=None,
    )

    response = client.get("/v1/cinemas/cin-1")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "MISS"


def test_get_cinema_cache_has_hit_header_on_repeat_request(
    client: TestClient, factory: MagicMock
) -> None:
    """Repeat requests for /cinemas/{id} have X-FastAPI-Cache: HIT header."""
    factory.get_cinema_use_case.execute.return_value = SimpleNamespace(
        id="cin-1",
        name="Test Cinema",
        address=None,
        city=None,
        website=None,
    )

    client.get("/v1/cinemas/cin-1")
    response = client.get("/v1/cinemas/cin-1")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "HIT"


def test_different_cinemas_have_separate_cache_entries(
    client: TestClient, factory: MagicMock
) -> None:
    """Requests for different cinema IDs have separate cache entries."""

    def mock_execute(request: GetCinemaUseCase.InputData) -> SimpleNamespace:
        return SimpleNamespace(
            id=request.cinema_id,
            name=f"Cinema {request.cinema_id}",
            address=None,
            city=None,
            website=None,
        )

    factory.get_cinema_use_case.execute.side_effect = mock_execute

    response1 = client.get("/v1/cinemas/cin-1")
    response2 = client.get("/v1/cinemas/cin-2")
    response1_again = client.get("/v1/cinemas/cin-1")

    assert response1.json()["id"] == "cin-1"
    assert response2.json()["id"] == "cin-2"
    assert response1_again.json() == response1.json()
    assert factory.get_cinema_use_case.execute.call_count == 2


def test_get_cinema_not_found_errors_are_not_cached(
    client: TestClient, factory: MagicMock
) -> None:
    """404 responses are not cached; repeat requests re-execute the use case."""
    factory.get_cinema_use_case.execute.side_effect = CinemaNotFoundError("not found")

    response1 = client.get("/v1/cinemas/missing")
    response2 = client.get("/v1/cinemas/missing")

    assert response1.status_code == 404
    assert response2.status_code == 404
    assert factory.get_cinema_use_case.execute.call_count == 2


def test_get_cinema_screenings_pagination(
    client: TestClient, factory: MagicMock
) -> None:
    """The router forwards page/size and reports the use case's total.

    The use case is mocked as already having applied pagination (as it does
    once page/size are pushed down to SQL), so this test verifies the
    router passes params through and reports ``total`` from the response
    rather than computing it from the page length.
    """
    factory.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
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
    factory.get_cinema_screenings_use_case.execute.assert_awaited_once_with(
        GetCinemaScreeningsUseCase.InputData(cinema_id="cin-1", page=2, size=2)
    )


def test_get_cinema_screenings_not_found(
    client: TestClient, factory: MagicMock
) -> None:
    """A missing cinema yields 404 with the standard error envelope."""
    factory.get_cinema_screenings_use_case.execute.side_effect = CinemaNotFoundError(
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
    client: TestClient, factory: MagicMock
) -> None:
    """A ValueError from the use case yields a 422 envelope."""
    factory.get_cinema_screenings_use_case.execute.side_effect = ValueError("bad input")

    response = client.get("/v1/cinemas/cin-1/screenings")

    assert response.status_code == 422
    body = response.json()
    assert body.pop("request_id")
    assert body == {"detail": "bad input", "error_code": "invalid_input"}


def test_get_cinema_screenings_ignores_unsupported_query_params(
    client: TestClient, factory: MagicMock
) -> None:
    """Filters beyond cinema scope aren't accepted — use GET /v1/screenings instead."""
    factory.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
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
    factory.get_cinema_screenings_use_case.execute.assert_awaited_once_with(
        GetCinemaScreeningsUseCase.InputData(cinema_id="cin-1", page=1, size=50)
    )


def test_get_movie(client: TestClient, factory: MagicMock) -> None:
    """GET /movies/{id} returns the movie."""
    factory.get_movie_use_case.execute.return_value = SimpleNamespace(
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
    factory.get_movie_use_case.execute.assert_awaited_once_with(
        GetMovieUseCase.InputData(movie_id="mov-1")
    )


def test_get_movie_not_found(client: TestClient, factory: MagicMock) -> None:
    """A missing movie yields 404 with the standard error envelope."""
    factory.get_movie_use_case.execute.side_effect = MovieNotFoundError("nope")

    response = client.get("/v1/movies/missing")

    assert response.status_code == 404
    body = response.json()
    assert body.pop("request_id")
    assert body == {"detail": "nope", "error_code": "not_found"}


def test_unhandled_exception_returns_generic_500(factory: MagicMock) -> None:
    """An unexpected exception from a use case yields a generic 500 envelope.

    Uses a separate TestClient with raise_server_exceptions=False: the
    default client fixture re-raises the original exception after the
    handler's response is sent (Starlette's ServerErrorMiddleware behavior),
    which would make this test raise instead of asserting on the response.
    """
    factory.get_movie_use_case.execute.side_effect = RuntimeError("db exploded")
    client = TestClient(create_app(factory=factory), raise_server_exceptions=False)

    response = client.get("/v1/movies/mov-1")

    assert response.status_code == 500
    body = response.json()
    assert body.pop("request_id")
    assert body == {
        "detail": "An unexpected RuntimeError occurred while processing the request.",
        "error_code": "internal_server_error",
    }


def test_list_movies(client: TestClient, factory: MagicMock) -> None:
    """GET /movies returns the use case's movies."""
    factory.list_movies_use_case.execute.return_value = SimpleNamespace(
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
    client: TestClient, factory: MagicMock
) -> None:
    """GET /movies calls list_movies_use_case with the title filter and paging."""
    factory.list_movies_use_case.execute.return_value = SimpleNamespace(
        movies=[], total=0
    )

    response = client.get("/v1/movies", params={"title": "Odyssey"})

    assert response.status_code == 200
    factory.list_movies_use_case.execute.assert_awaited_once_with(
        ListMoviesUseCase.InputData(title="Odyssey", page=1, size=50)
    )


def test_list_movies_converts_ids_to_tuple(
    client: TestClient, factory: MagicMock
) -> None:
    """GET /movies maps repeated IDs into immutable use-case DTO input."""
    factory.list_movies_use_case.execute.return_value = SimpleNamespace(
        movies=[], total=0
    )

    response = client.get(
        "/v1/movies",
        params=[("ids", "mov-1"), ("ids", "mov-2"), ("size", "2")],
    )

    assert response.status_code == 200
    factory.list_movies_use_case.execute.assert_awaited_once_with(
        ListMoviesUseCase.InputData(ids=("mov-1", "mov-2"), page=1, size=2)
    )


def test_list_movies_pagination(client: TestClient, factory: MagicMock) -> None:
    """The router forwards page/size and reports the use case's total."""
    factory.list_movies_use_case.execute.return_value = SimpleNamespace(
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
    factory.list_movies_use_case.execute.assert_awaited_once_with(
        ListMoviesUseCase.InputData(title=None, page=2, size=2)
    )


def test_list_movies_size_out_of_range_is_rejected(
    client: TestClient, factory: MagicMock
) -> None:
    """A size above the max page size is rejected with a 422."""
    response = client.get("/v1/movies", params={"size": 101})

    assert response.status_code == 422


def test_list_cinemas_is_cached(client: TestClient, factory: MagicMock) -> None:
    """A second identical request reuses the cached result instead of re-executing."""
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
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
    factory.list_cinemas_use_case.execute.assert_awaited_once()


def test_get_movie_is_cached(client: TestClient, factory: MagicMock) -> None:
    """A second request for the same movie reuses the cached response."""
    factory.get_movie_use_case.execute.return_value = SimpleNamespace(
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
    factory.get_movie_use_case.execute.assert_awaited_once()


def test_list_movies_is_cached(client: TestClient, factory: MagicMock) -> None:
    """A second identical request reuses the cached result instead of re-executing."""
    factory.list_movies_use_case.execute.return_value = SimpleNamespace(
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
    factory.list_movies_use_case.execute.assert_awaited_once()


def test_get_cinema_screenings_is_cached(
    client: TestClient, factory: MagicMock
) -> None:
    """A second request reuses the cached response."""
    factory.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
        total=0,
    )

    first = client.get("/v1/cinemas/cin-1/screenings")
    second = client.get("/v1/cinemas/cin-1/screenings")

    assert first.status_code == 200
    assert second.json() == first.json()
    factory.get_cinema_screenings_use_case.execute.assert_awaited_once()


def test_list_cinemas_cache_has_miss_header_on_first_request(
    client: TestClient, factory: MagicMock
) -> None:
    """The first request for /cinemas has X-FastAPI-Cache: MISS header."""
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )

    response = client.get("/v1/cinemas")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "MISS"


def test_list_cinemas_cache_has_hit_header_on_repeat_request(
    client: TestClient, factory: MagicMock
) -> None:
    """Repeat requests for /cinemas have X-FastAPI-Cache: HIT header."""
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )

    client.get("/v1/cinemas")
    response = client.get("/v1/cinemas")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "HIT"


def test_get_movie_cache_has_miss_header_on_first_request(
    client: TestClient, factory: MagicMock
) -> None:
    """The first request for /movies/{id} has X-FastAPI-Cache: MISS header."""
    factory.get_movie_use_case.execute.return_value = SimpleNamespace(
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
    client: TestClient, factory: MagicMock
) -> None:
    """Repeat requests for /movies/{id} have X-FastAPI-Cache: HIT header."""
    factory.get_movie_use_case.execute.return_value = SimpleNamespace(
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
    client: TestClient, factory: MagicMock
) -> None:
    """The first screenings request has an X-FastAPI-Cache MISS header."""
    factory.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
        total=0,
    )

    response = client.get("/v1/cinemas/cin-1/screenings")

    assert response.status_code == 200
    assert response.headers.get("X-FastAPI-Cache") == "MISS"


def test_get_cinema_screenings_cache_has_hit_header_on_repeat_request(
    client: TestClient, factory: MagicMock
) -> None:
    """Repeat requests for /cinemas/{id}/screenings have X-FastAPI-Cache: HIT header."""
    factory.get_cinema_screenings_use_case.execute.return_value = SimpleNamespace(
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
    client: TestClient, factory: MagicMock
) -> None:
    """Requests for different movie IDs have separate cache entries."""

    def mock_execute(request: GetMovieUseCase.InputData) -> SimpleNamespace:
        return SimpleNamespace(
            id=request.movie_id,
            title=f"Movie {request.movie_id}",
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

    factory.get_movie_use_case.execute.side_effect = mock_execute

    response1 = client.get("/v1/movies/mov-1")
    response2 = client.get("/v1/movies/mov-2")
    response1_again = client.get("/v1/movies/mov-1")

    assert response1.json()["id"] == "mov-1"
    assert response2.json()["id"] == "mov-2"
    assert response1_again.json() == response1.json()
    assert factory.get_movie_use_case.execute.call_count == 2


def test_not_found_errors_are_not_cached(
    client: TestClient, factory: MagicMock
) -> None:
    """404 responses are not cached; repeat requests re-execute the use case."""
    factory.get_movie_use_case.execute.side_effect = MovieNotFoundError("not found")

    response1 = client.get("/v1/movies/missing")
    response2 = client.get("/v1/movies/missing")

    assert response1.status_code == 404
    assert response2.status_code == 404
    assert factory.get_movie_use_case.execute.call_count == 2


def test_list_cinemas_with_name_filter_creates_separate_cache_entry(
    client: TestClient, factory: MagicMock
) -> None:
    """Query parameter differences create separate cache entries."""

    def mock_list(request: ListCinemasUseCase.InputData) -> SimpleNamespace:
        if request.name == "Cineplex":
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

    factory.list_cinemas_use_case.execute.side_effect = mock_list

    response1 = client.get("/v1/cinemas", params={"name": "Cineplex"})
    response2 = client.get("/v1/cinemas", params={"name": "Landmark"})
    response1_again = client.get("/v1/cinemas", params={"name": "Cineplex"})

    assert response1.json()["items"][0]["name"] == "Cineplex Downtown"
    assert response2.json()["items"][0]["name"] == "Landmark Cinemas"
    assert response1_again.json() == response1.json()
    assert response1_again.headers.get("X-FastAPI-Cache") == "HIT"
    assert factory.list_cinemas_use_case.execute.call_count == 2


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


def test_cors_headers_present_when_configured(
    monkeypatch: pytest.MonkeyPatch, factory: MagicMock
) -> None:
    """CORS headers are returned when MARQUISE_API_CORS_ORIGINS is set."""
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "http://localhost:3000")
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    client = TestClient(create_app(factory=factory))

    response = client.get(
        "/v1/cinemas",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_preflight_when_configured(
    monkeypatch: pytest.MonkeyPatch, factory: MagicMock
) -> None:
    """OPTIONS preflight requests return CORS headers when configured."""
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "http://localhost:3000")
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    client = TestClient(create_app(factory=factory))

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


def test_cors_origin_not_allowed_rejected(
    monkeypatch: pytest.MonkeyPatch, factory: MagicMock
) -> None:
    """Requests from an origin not in the allowed list get no CORS headers."""
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "http://localhost:3000")
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    client = TestClient(create_app(factory=factory))

    response = client.get(
        "/v1/cinemas",
        headers={"Origin": "https://evil.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_rate_limit_headers_present_on_success(
    client: TestClient, factory: MagicMock
) -> None:
    """A normal request under the limit reports rate-limit headers."""
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )

    response = client.get("/v1/cinemas")

    assert response.status_code == 200
    assert "x-ratelimit-limit" in response.headers
    assert "x-ratelimit-remaining" in response.headers
    assert "x-ratelimit-reset" in response.headers


def test_rate_limit_exceeded_returns_429(
    monkeypatch: pytest.MonkeyPatch, factory: MagicMock
) -> None:
    """A client exceeding the configured rate limit gets a 429 with Retry-After."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    client = TestClient(create_app(factory=factory))

    first = client.get("/v1/cinemas")
    second = client.get("/v1/cinemas")

    assert first.status_code == 200
    assert second.status_code == 429
    assert "retry-after" in second.headers
    assert "error" in second.json()


def test_health_is_exempt_from_rate_limiting(
    monkeypatch: pytest.MonkeyPatch, factory: MagicMock
) -> None:
    """/health keeps responding 200 even past the configured rate limit."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    client = TestClient(create_app(factory=factory))

    responses = [client.get("/health") for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)


def test_rate_limit_is_configurable_via_env_var(
    monkeypatch: pytest.MonkeyPatch, factory: MagicMock
) -> None:
    """A higher configured limit allows more requests before a 429."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "5/minute")
    factory.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    client = TestClient(create_app(factory=factory))

    responses = [client.get("/v1/cinemas") for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)
    assert client.get("/v1/cinemas").status_code == 429


def test_search_screenings(client: TestClient, factory: MagicMock) -> None:
    """GET /screenings returns the use case's screenings."""
    factory.search_screenings_use_case.execute.return_value = SimpleNamespace(
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
    client: TestClient, factory: MagicMock
) -> None:
    """GET /screenings forwards all query params to the use case."""
    factory.search_screenings_use_case.execute.return_value = SimpleNamespace(
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
    factory.search_screenings_use_case.execute.assert_awaited_once_with(
        SearchScreeningsUseCase.InputData(
            movie="Odyssey",
            movie_id="mov-1",
            cinema_id="cin-1",
            language="V.O.",
            page=1,
            size=50,
        )
    )


def test_search_screenings_pagination(client: TestClient, factory: MagicMock) -> None:
    """GET /screenings supports page/size pagination."""
    factory.search_screenings_use_case.execute.return_value = SimpleNamespace(
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
    factory.search_screenings_use_case.execute.assert_awaited_once()


def test_search_screenings_size_out_of_range_is_rejected(
    client: TestClient,
) -> None:
    """A size above the max page size is rejected with a 422."""
    response = client.get("/v1/screenings", params={"size": 101})

    assert response.status_code == 422


def test_search_screenings_invalid_range_returns_422_envelope(
    client: TestClient, factory: MagicMock
) -> None:
    """An invalid date range from the use case is surfaced as a 422 envelope."""
    factory.search_screenings_use_case.execute.side_effect = ValueError(
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
    client: TestClient, factory: MagicMock
) -> None:
    """Repeated identical requests to /screenings are not served from cache."""
    factory.search_screenings_use_case.execute.return_value = SimpleNamespace(
        screenings=[], total=0
    )

    first = client.get("/v1/screenings")
    second = client.get("/v1/screenings")

    assert first.status_code == 200
    assert second.status_code == 200
    assert factory.search_screenings_use_case.execute.await_count == 2


def test_get_screening(client: TestClient, factory: MagicMock) -> None:
    """GET /screenings/{id} returns the screening."""
    factory.get_screening_use_case.execute.return_value = SimpleNamespace(
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
    factory.get_screening_use_case.execute.assert_awaited_once_with(
        GetScreeningUseCase.InputData(screening_id="scr-1")
    )


def test_get_screening_not_found(client: TestClient, factory: MagicMock) -> None:
    """GET /screenings/{id} returns a 404 envelope for a missing screening."""
    factory.get_screening_use_case.execute.side_effect = ScreeningNotFoundError(
        "A screening with ID 'missing' was not found"
    )

    response = client.get("/v1/screenings/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "not_found"


def test_get_movie_screenings(client: TestClient, factory: MagicMock) -> None:
    """GET /movies/{id}/screenings returns all of the movie's screenings."""
    factory.get_movie_screenings_use_case.execute.return_value = SimpleNamespace(
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
    client: TestClient, factory: MagicMock
) -> None:
    """Filters beyond movie scope aren't accepted — use GET /v1/screenings instead."""
    factory.get_movie_screenings_use_case.execute.return_value = SimpleNamespace(
        movie_id="mov-1", movie_title="The Odyssey", screenings=[], total=0
    )

    response = client.get(
        "/v1/movies/mov-1/screenings",
        params={"cinema_id": "cin-1", "language": "V.O.", "from": "2026-06-27"},
    )

    assert response.status_code == 200
    factory.get_movie_screenings_use_case.execute.assert_awaited_once_with(
        GetMovieScreeningsUseCase.InputData(movie_id="mov-1", page=1, size=50)
    )


def test_get_movie_screenings_not_found(client: TestClient, factory: MagicMock) -> None:
    """GET /movies/{id}/screenings returns a 404 envelope for a missing movie."""
    factory.get_movie_screenings_use_case.execute.side_effect = MovieNotFoundError(
        "A movie with ID 'missing' was not found"
    )

    response = client.get("/v1/movies/missing/screenings")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "not_found"


def test_get_cinema_movies(client: TestClient, factory: MagicMock) -> None:
    """GET /cinemas/{id}/movies returns the cinema's distinct movies."""
    factory.get_cinema_movies_use_case.execute.return_value = SimpleNamespace(
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

    factory.get_cinema_movies_use_case.execute.assert_awaited_once_with(
        GetCinemaMoviesUseCase.InputData(
            cinema_id="cin-1",
            start_date=datetime(2026, 6, 27),
            end_date=datetime(2026, 6, 28),
            page=1,
            size=50,
        )
    )


def test_get_cinema_movies_not_found(client: TestClient, factory: MagicMock) -> None:
    """GET /cinemas/{id}/movies returns a 404 envelope for an unknown cinema."""
    factory.get_cinema_movies_use_case.execute.side_effect = CinemaNotFoundError(
        "A cinema with ID 'missing' was not found"
    )

    response = client.get("/v1/cinemas/missing/movies")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "not_found"


def test_get_cinema_movies_pagination(client: TestClient, factory: MagicMock) -> None:
    """The router forwards page/size and reports the use case's total."""
    factory.get_cinema_movies_use_case.execute.return_value = SimpleNamespace(
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
