"""Tests for the read-only FastAPI application.

The DI container is replaced with a MagicMock whose use cases are stubbed,
so these tests touch no database.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, PropertyMock, create_autospec

import pytest
from fastapi.testclient import TestClient
from fastapi_cache.backends.inmemory import InMemoryBackend

from marquise import (
    BrowseScreeningMoviesQuery,
    CinemaNotFoundError,
    CinemaUseCases,
    CountScreeningDaysQuery,
    GetCinemaMoviesUseCase,
    GetCinemaScreeningsQuery,
    GetCinemaUseCase,
    GetMovieScreeningsQuery,
    GetMovieUseCase,
    GetScreeningQuery,
    ListCinemasUseCase,
    ListMoviesUseCase,
    MarquiseFactory,
    MovieNotFoundError,
    MovieUseCases,
    ScreeningNotFoundError,
    ScreeningUseCases,
    SearchScreeningsQuery,
    TooManyScreeningDaysError,
)
from marquise_api.app import CACHE_PREFIX, create_app


@pytest.fixture(autouse=True)
def _clear_response_cache() -> None:
    """Clear cached responses after each test."""
    yield
    asyncio.run(InMemoryBackend().clear(namespace=CACHE_PREFIX))


@pytest.fixture
def factory() -> MagicMock:
    """Provide fake factory with autospecced read use cases."""
    fake = create_autospec(MarquiseFactory, instance=True)
    fake.cinemas = create_autospec(CinemaUseCases, instance=True)
    fake.cinemas.list_cinemas_use_case = create_autospec(
        ListCinemasUseCase, instance=True
    )
    fake.cinemas.get_cinema_use_case = create_autospec(GetCinemaUseCase, instance=True)
    fake.cinemas.get_cinema_screenings_query = create_autospec(
        GetCinemaScreeningsQuery, instance=True
    )
    fake.cinemas.get_cinema_movies_use_case = create_autospec(
        GetCinemaMoviesUseCase, instance=True
    )
    fake.movies = create_autospec(MovieUseCases, instance=True)
    fake.movies.list_movies_use_case = create_autospec(ListMoviesUseCase, instance=True)
    fake.movies.get_movie_use_case = create_autospec(GetMovieUseCase, instance=True)
    fake.movies.get_movie_screenings_query = create_autospec(
        GetMovieScreeningsQuery, instance=True
    )
    fake.screenings = create_autospec(ScreeningUseCases, instance=True)
    fake.screenings.search_screenings_query = create_autospec(
        SearchScreeningsQuery, instance=True
    )
    fake.screenings.get_screening_query = create_autospec(
        GetScreeningQuery, instance=True
    )
    return fake


@pytest.fixture
def client(factory: MagicMock, client_opener: Callable[..., TestClient]) -> TestClient:
    """Provide a TestClient backed by the fake container."""
    return client_opener(factory)


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


def test_app_holds_one_factory_session_for_its_lifetime(
    monkeypatch: pytest.MonkeyPatch, factory: MagicMock
) -> None:
    """Without an injected factory, startup opens a session and shutdown closes it."""
    session_events: list[str] = []

    @asynccontextmanager
    async def fake_factory_session() -> AsyncIterator[MagicMock]:
        session_events.append("opened")
        yield factory
        session_events.append("closed")

    monkeypatch.setattr("marquise_api.app.create_factory_session", fake_factory_session)
    factory.check_database_health = AsyncMock(return_value=True)

    with TestClient(create_app()) as client:
        assert client.get("/ready").status_code == 200
        assert session_events == ["opened"]

    assert session_events == ["opened", "closed"]


def test_ready_is_exempt_from_rate_limiting(
    monkeypatch: pytest.MonkeyPatch,
    factory: MagicMock,
    client_opener: Callable[..., TestClient],
) -> None:
    """/ready keeps responding even past the configured rate limit."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    factory.check_database_health = AsyncMock(return_value=True)
    client = client_opener(factory)

    responses = [client.get("/ready") for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)


def test_list_cinemas(client: TestClient, factory: MagicMock) -> None:
    """GET /cinemas returns the use case's cinemas."""
    factory.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
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
    factory.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )

    response = client.get("/v1/cinemas", params={"name": "Cineplex"})

    assert response.status_code == 200
    factory.cinemas.list_cinemas_use_case.execute.assert_awaited_once_with(
        ListCinemasUseCase.InputData(name="Cineplex", page=1, size=50)
    )


def test_get_cinema_screenings(client: TestClient, factory: MagicMock) -> None:
    """GET /cinemas/{id}/screenings returns screenings in range."""
    factory.cinemas.get_cinema_screenings_query.execute.return_value = SimpleNamespace(
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
    factory.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
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
    factory.cinemas.list_cinemas_use_case.execute.assert_awaited_once_with(
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
    factory.cinemas.get_cinema_use_case.execute.return_value = SimpleNamespace(
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
    factory.cinemas.get_cinema_use_case.execute.assert_awaited_once_with(
        GetCinemaUseCase.InputData(cinema_id="cin-1")
    )


def test_get_cinema_not_found(client: TestClient, factory: MagicMock) -> None:
    """A missing cinema yields 404 with the standard error envelope."""
    factory.cinemas.get_cinema_use_case.execute.side_effect = CinemaNotFoundError(
        "nope"
    )

    response = client.get("/v1/cinemas/missing")

    assert response.status_code == 404
    body = response.json()
    assert body.pop("request_id")
    assert body == {"detail": "nope", "error_code": "not_found"}


def test_get_cinema_is_cached(client: TestClient, factory: MagicMock) -> None:
    """A second request for the same cinema reuses the cached response."""
    factory.cinemas.get_cinema_use_case.execute.return_value = SimpleNamespace(
        id="cin-1",
        name="Cinema One",
        address=None,
        city=None,
        website=None,
    )

    first = client.get("/v1/cinemas/cin-1")
    second = client.get("/v1/cinemas/cin-1")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers.get("X-FastAPI-Cache") == "MISS"
    assert second.headers.get("X-FastAPI-Cache") == "HIT"
    assert second.json() == first.json()
    factory.cinemas.get_cinema_use_case.execute.assert_awaited_once()


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

    factory.cinemas.get_cinema_use_case.execute.side_effect = mock_execute

    response1 = client.get("/v1/cinemas/cin-1")
    response2 = client.get("/v1/cinemas/cin-2")
    response1_again = client.get("/v1/cinemas/cin-1")

    assert response1.json()["id"] == "cin-1"
    assert response2.json()["id"] == "cin-2"
    assert response1_again.json() == response1.json()
    assert factory.cinemas.get_cinema_use_case.execute.call_count == 2


def test_get_cinema_not_found_errors_are_not_cached(
    client: TestClient, factory: MagicMock
) -> None:
    """404 responses are not cached; repeat requests re-execute the use case."""
    factory.cinemas.get_cinema_use_case.execute.side_effect = CinemaNotFoundError(
        "not found"
    )

    response1 = client.get("/v1/cinemas/missing")
    response2 = client.get("/v1/cinemas/missing")

    assert response1.status_code == 404
    assert response2.status_code == 404
    assert factory.cinemas.get_cinema_use_case.execute.call_count == 2


def test_get_cinema_screenings_pagination(
    client: TestClient, factory: MagicMock
) -> None:
    """The router forwards page/size and reports the use case's total.

    The use case is mocked as already having applied pagination (as it does
    once page/size are pushed down to SQL), so this test verifies the
    router passes params through and reports ``total`` from the response
    rather than computing it from the page length.
    """
    factory.cinemas.get_cinema_screenings_query.execute.return_value = SimpleNamespace(
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
    factory.cinemas.get_cinema_screenings_query.execute.assert_awaited_once_with(
        GetCinemaScreeningsQuery.InputData(cinema_id="cin-1", page=2, size=2)
    )


def test_get_cinema_screenings_not_found(
    client: TestClient, factory: MagicMock
) -> None:
    """A missing cinema yields 404 with the standard error envelope."""
    factory.cinemas.get_cinema_screenings_query.execute.side_effect = (
        CinemaNotFoundError("nope")
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
    factory.cinemas.get_cinema_screenings_query.execute.side_effect = ValueError(
        "bad input"
    )

    response = client.get("/v1/cinemas/cin-1/screenings")

    assert response.status_code == 422
    body = response.json()
    assert body.pop("request_id")
    assert body == {"detail": "bad input", "error_code": "invalid_input"}


def test_get_cinema_screenings_ignores_unsupported_query_params(
    client: TestClient, factory: MagicMock
) -> None:
    """Filters beyond cinema scope aren't accepted — use GET /v1/screenings instead."""
    factory.cinemas.get_cinema_screenings_query.execute.return_value = SimpleNamespace(
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
    factory.cinemas.get_cinema_screenings_query.execute.assert_awaited_once_with(
        GetCinemaScreeningsQuery.InputData(cinema_id="cin-1", page=1, size=50)
    )


def test_get_movie(client: TestClient, factory: MagicMock) -> None:
    """GET /movies/{id} returns the movie."""
    factory.movies.get_movie_use_case.execute.return_value = SimpleNamespace(
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
        tmdb_rating=8.1,
        tmdb_vote_count=1234,
    )

    response = client.get("/v1/movies/mov-1")

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "The Odyssey"
    assert body["release_year"] == 2026
    assert body["tmdb_rating"] == 8.1
    assert body["tmdb_vote_count"] == 1234
    factory.movies.get_movie_use_case.execute.assert_awaited_once_with(
        GetMovieUseCase.InputData(movie_id="mov-1")
    )


def test_get_movie_not_found(client: TestClient, factory: MagicMock) -> None:
    """A missing movie yields 404 with the standard error envelope."""
    factory.movies.get_movie_use_case.execute.side_effect = MovieNotFoundError("nope")

    response = client.get("/v1/movies/missing")

    assert response.status_code == 404
    body = response.json()
    assert body.pop("request_id")
    assert body == {"detail": "nope", "error_code": "not_found"}


def test_unhandled_exception_returns_generic_500(
    factory: MagicMock, client_opener: Callable[..., TestClient]
) -> None:
    """An unexpected exception from a use case yields a generic 500 envelope.

    Uses a separate TestClient with raise_server_exceptions=False: the
    default client fixture re-raises the original exception after the
    handler's response is sent (Starlette's ServerErrorMiddleware behavior),
    which would make this test raise instead of asserting on the response.
    """
    factory.movies.get_movie_use_case.execute.side_effect = RuntimeError("db exploded")
    client = client_opener(factory, raise_server_exceptions=False)

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
    factory.movies.list_movies_use_case.execute.return_value = SimpleNamespace(
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
                tmdb_rating=None,
                tmdb_vote_count=None,
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
    assert body["items"][0]["tmdb_rating"] is None
    assert body["items"][0]["tmdb_vote_count"] is None
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["size"] == 50


def test_list_movies_delegates_to_use_case_with_title_filter(
    client: TestClient, factory: MagicMock
) -> None:
    """GET /movies calls list_movies_use_case with the title filter and paging."""
    factory.movies.list_movies_use_case.execute.return_value = SimpleNamespace(
        movies=[], total=0
    )

    response = client.get("/v1/movies", params={"title": "Odyssey"})

    assert response.status_code == 200
    factory.movies.list_movies_use_case.execute.assert_awaited_once_with(
        ListMoviesUseCase.InputData(title="Odyssey", page=1, size=50)
    )


def test_list_movies_converts_ids_to_tuple(
    client: TestClient, factory: MagicMock
) -> None:
    """GET /movies maps repeated IDs into immutable use-case DTO input."""
    factory.movies.list_movies_use_case.execute.return_value = SimpleNamespace(
        movies=[], total=0
    )

    response = client.get(
        "/v1/movies",
        params=[("ids", "mov-1"), ("ids", "mov-2"), ("size", "2")],
    )

    assert response.status_code == 200
    factory.movies.list_movies_use_case.execute.assert_awaited_once_with(
        ListMoviesUseCase.InputData(ids=("mov-1", "mov-2"), page=1, size=2)
    )


def test_list_movies_pagination(client: TestClient, factory: MagicMock) -> None:
    """The router forwards page/size and reports the use case's total."""
    factory.movies.list_movies_use_case.execute.return_value = SimpleNamespace(
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
    factory.movies.list_movies_use_case.execute.assert_awaited_once_with(
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
    factory.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
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
    assert first.headers.get("X-FastAPI-Cache") == "MISS"
    assert second.status_code == 200
    assert second.headers.get("X-FastAPI-Cache") == "HIT"
    assert first.json() == second.json()
    factory.cinemas.list_cinemas_use_case.execute.assert_awaited_once()


def test_get_movie_is_cached(client: TestClient, factory: MagicMock) -> None:
    """A second request for the same movie reuses the cached response."""
    factory.movies.get_movie_use_case.execute.return_value = SimpleNamespace(
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
    assert second.status_code == 200
    assert first.headers.get("X-FastAPI-Cache") == "MISS"
    assert second.headers.get("X-FastAPI-Cache") == "HIT"
    assert second.json() == first.json()
    factory.movies.get_movie_use_case.execute.assert_awaited_once()


def test_list_movies_is_cached(client: TestClient, factory: MagicMock) -> None:
    """A second identical request reuses the cached result instead of re-executing."""
    factory.movies.list_movies_use_case.execute.return_value = SimpleNamespace(
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
    factory.movies.list_movies_use_case.execute.assert_awaited_once()


def test_get_cinema_screenings_is_cached(
    client: TestClient, factory: MagicMock
) -> None:
    """A second request reuses the cached response."""
    factory.cinemas.get_cinema_screenings_query.execute.return_value = SimpleNamespace(
        cinema_id="cin-1",
        cinema_name="Cinema One",
        screenings=[],
        total=0,
    )

    first = client.get("/v1/cinemas/cin-1/screenings")
    second = client.get("/v1/cinemas/cin-1/screenings")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.headers.get("X-FastAPI-Cache") == "MISS"
    assert second.headers.get("X-FastAPI-Cache") == "HIT"
    assert second.json() == first.json()
    factory.cinemas.get_cinema_screenings_query.execute.assert_awaited_once()


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

    factory.movies.get_movie_use_case.execute.side_effect = mock_execute

    response1 = client.get("/v1/movies/mov-1")
    response2 = client.get("/v1/movies/mov-2")
    response1_again = client.get("/v1/movies/mov-1")

    assert response1.json()["id"] == "mov-1"
    assert response2.json()["id"] == "mov-2"
    assert response1_again.json() == response1.json()
    assert factory.movies.get_movie_use_case.execute.call_count == 2


def test_not_found_errors_are_not_cached(
    client: TestClient, factory: MagicMock
) -> None:
    """404 responses are not cached; repeat requests re-execute the use case."""
    factory.movies.get_movie_use_case.execute.side_effect = MovieNotFoundError(
        "not found"
    )

    response1 = client.get("/v1/movies/missing")
    response2 = client.get("/v1/movies/missing")

    assert response1.status_code == 404
    assert response2.status_code == 404
    assert factory.movies.get_movie_use_case.execute.call_count == 2


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

    factory.cinemas.list_cinemas_use_case.execute.side_effect = mock_list

    response1 = client.get("/v1/cinemas", params={"name": "Cineplex"})
    response2 = client.get("/v1/cinemas", params={"name": "Landmark"})
    response1_again = client.get("/v1/cinemas", params={"name": "Cineplex"})

    assert response1.json()["items"][0]["name"] == "Cineplex Downtown"
    assert response2.json()["items"][0]["name"] == "Landmark Cinemas"
    assert response1_again.json() == response1.json()
    assert response1_again.headers.get("X-FastAPI-Cache") == "HIT"
    assert factory.cinemas.list_cinemas_use_case.execute.call_count == 2


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
    monkeypatch: pytest.MonkeyPatch,
    factory: MagicMock,
    client_opener: Callable[..., TestClient],
) -> None:
    """CORS headers are returned when MARQUISE_API_CORS_ORIGINS is set."""
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "http://localhost:3000")
    factory.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    client = client_opener(factory)

    response = client.get(
        "/v1/cinemas",
        headers={"Origin": "http://localhost:3000"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_preflight_when_configured(
    monkeypatch: pytest.MonkeyPatch,
    factory: MagicMock,
    client_opener: Callable[..., TestClient],
) -> None:
    """OPTIONS preflight requests return CORS headers when configured."""
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "http://localhost:3000")
    factory.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    client = client_opener(factory)

    response = client.options(
        "/v1/cinemas",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert set(response.headers["access-control-allow-methods"].split(", ")) == {
        "GET",
        "POST",
    }


def test_cors_origin_not_allowed_rejected(
    monkeypatch: pytest.MonkeyPatch,
    factory: MagicMock,
    client_opener: Callable[..., TestClient],
) -> None:
    """Requests from an origin not in the allowed list get no CORS headers."""
    monkeypatch.setenv("MARQUISE_API_CORS_ORIGINS", "http://localhost:3000")
    factory.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    client = client_opener(factory)

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
    factory.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )

    response = client.get("/v1/cinemas")

    assert response.status_code == 200
    assert "x-ratelimit-limit" in response.headers
    assert "x-ratelimit-remaining" in response.headers
    assert "x-ratelimit-reset" in response.headers


def test_rate_limit_exceeded_returns_429(
    monkeypatch: pytest.MonkeyPatch,
    factory: MagicMock,
    client_opener: Callable[..., TestClient],
) -> None:
    """A client exceeding the configured rate limit gets a 429 with Retry-After."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    factory.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    client = client_opener(factory)

    first = client.get("/v1/cinemas")
    second = client.get("/v1/cinemas")

    assert first.status_code == 200
    assert second.status_code == 429
    assert "retry-after" in second.headers
    assert "error" in second.json()


def test_health_is_exempt_from_rate_limiting(
    monkeypatch: pytest.MonkeyPatch,
    factory: MagicMock,
    client_opener: Callable[..., TestClient],
) -> None:
    """/health keeps responding 200 even past the configured rate limit."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "1/minute")
    client = client_opener(factory)

    responses = [client.get("/health") for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)


def test_rate_limit_is_configurable_via_env_var(
    monkeypatch: pytest.MonkeyPatch,
    factory: MagicMock,
    client_opener: Callable[..., TestClient],
) -> None:
    """A higher configured limit allows more requests before a 429."""
    monkeypatch.setenv("MARQUISE_API_RATE_LIMIT", "5/minute")
    factory.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    client = client_opener(factory)

    responses = [client.get("/v1/cinemas") for _ in range(5)]

    assert all(response.status_code == 200 for response in responses)
    assert client.get("/v1/cinemas").status_code == 429


def test_search_screenings(client: TestClient, factory: MagicMock) -> None:
    """GET /screenings returns the use case's screenings."""
    factory.screenings.search_screenings_query.execute.return_value = SimpleNamespace(
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
    factory.screenings.search_screenings_query.execute.return_value = SimpleNamespace(
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
    factory.screenings.search_screenings_query.execute.assert_awaited_once_with(
        SearchScreeningsQuery.InputData(
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
    factory.screenings.search_screenings_query.execute.return_value = SimpleNamespace(
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
    factory.screenings.search_screenings_query.execute.assert_awaited_once()


@pytest.mark.parametrize(
    "url",
    [
        "/v1/screenings?size=101",
        "/v1/cinemas/cin-1/movies?from=2026-11-20",
        "/v1/cinemas/cin-1/movies?to=2026-11-27",
        "/v1/cinemas/cin-1/movies?from=2026-11-20T18:00:00&to=2026-11-27T18:00:00Z",
        "/v1/cinemas/cin-1/movies?from=2026-11-20T18:00:00Z&to=2026-11-27T18:00:00",
    ],
)
def test_invalid_screening_query_is_rejected(
    client: TestClient, factory: MagicMock, url: str
) -> None:
    """Oversized pages and naive cinema movie dates fail before querying."""
    response = client.get(url)
    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_input"
    factory.screenings.search_screenings_query.execute.assert_not_awaited()
    factory.cinemas.get_cinema_movies_use_case.execute.assert_not_awaited()


def test_search_screenings_invalid_range_returns_422_envelope(
    client: TestClient, factory: MagicMock
) -> None:
    """An invalid date range from the use case is surfaced as a 422 envelope."""
    factory.screenings.search_screenings_query.execute.side_effect = ValueError(
        "start_date must not be after end_date"
    )

    response = client.get(
        "/v1/screenings",
        params={"from": "2026-06-28T00:00:00Z", "to": "2026-06-27T00:00:00Z"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "invalid_input"


def test_search_screenings_is_cached(client: TestClient, factory: MagicMock) -> None:
    """Repeated identical requests to /screenings reuse cached response."""
    factory.screenings.search_screenings_query.execute.return_value = SimpleNamespace(
        screenings=[], total=0
    )

    first = client.get("/v1/screenings")
    second = client.get("/v1/screenings")

    assert first.status_code == 200
    assert first.headers.get("X-FastAPI-Cache") == "MISS"
    assert second.status_code == 200
    assert second.headers.get("X-FastAPI-Cache") == "HIT"
    assert factory.screenings.search_screenings_query.execute.await_count == 1


def test_search_screenings_cache_ignores_fresh_injected_query(
    client: TestClient, factory: MagicMock
) -> None:
    """Same request hits cache when dependency returns a fresh query each time."""
    first_query = create_autospec(SearchScreeningsQuery, instance=True)
    first_query.execute.return_value = SimpleNamespace(screenings=[], total=0)
    second_query = create_autospec(SearchScreeningsQuery, instance=True)
    type(factory.screenings).search_screenings_query = PropertyMock(
        side_effect=[first_query, second_query]
    )

    first = client.get("/v1/screenings")
    second = client.get("/v1/screenings")

    assert first.headers.get("X-FastAPI-Cache") == "MISS"
    assert second.headers.get("X-FastAPI-Cache") == "HIT"
    first_query.execute.assert_awaited_once()
    second_query.execute.assert_not_awaited()


def test_search_screenings_different_filters_use_separate_cache_entries(
    client: TestClient, factory: MagicMock
) -> None:
    """Different query strings get separate cache entries and re-execute."""
    factory.screenings.search_screenings_query.execute.return_value = SimpleNamespace(
        screenings=[], total=0
    )

    first = client.get("/v1/screenings", params={"from": "2026-06-27T00:00:00Z"})
    second = client.get("/v1/screenings", params={"from": "2026-06-28T00:00:00Z"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers.get("X-FastAPI-Cache") == "MISS"
    assert factory.screenings.search_screenings_query.execute.await_count == 2


def test_search_screenings_different_pages_use_separate_cache_entries(
    client: TestClient, factory: MagicMock
) -> None:
    """Different page/size combinations get separate cache entries."""
    factory.screenings.search_screenings_query.execute.return_value = SimpleNamespace(
        screenings=[], total=0
    )

    first = client.get("/v1/screenings", params={"page": 1, "size": 100})
    second = client.get("/v1/screenings", params={"page": 2, "size": 100})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.headers.get("X-FastAPI-Cache") == "MISS"
    assert factory.screenings.search_screenings_query.execute.await_count == 2


def test_get_screening(client: TestClient, factory: MagicMock) -> None:
    """GET /screenings/{id} returns the screening."""
    factory.screenings.get_screening_query.execute.return_value = (
        GetScreeningQuery.OutputData(
            id="scr-1",
            movie_id="mov-1",
            movie_title="The Odyssey",
            cinema_id="cin-1",
            cinema_name="Cinema One",
            showtime=datetime.fromisoformat("2026-06-27T19:30:00+00:00"),
            ticket_url=None,
            room=None,
            language=None,
        )
    )

    response = client.get("/v1/screenings/scr-1")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "id": "scr-1",
        "movie_id": "mov-1",
        "movie_title": "The Odyssey",
        "cinema_id": "cin-1",
        "cinema_name": "Cinema One",
        "showtime": "2026-06-27T19:30:00Z",
        "ticket_url": None,
        "room": None,
        "language": None,
    }
    factory.screenings.get_screening_query.execute.assert_awaited_once_with(
        GetScreeningQuery.InputData(screening_id="scr-1")
    )


def test_get_screening_not_found(client: TestClient, factory: MagicMock) -> None:
    """GET /screenings/{id} returns a 404 envelope for a missing screening."""
    factory.screenings.get_screening_query.execute.side_effect = ScreeningNotFoundError(
        "A screening with ID 'missing' was not found"
    )

    response = client.get("/v1/screenings/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "not_found"


def test_get_movie_screenings(client: TestClient, factory: MagicMock) -> None:
    """GET /movies/{id}/screenings returns all of the movie's screenings."""
    factory.movies.get_movie_screenings_query.execute.return_value = SimpleNamespace(
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


def test_get_movie_screenings_without_from_keeps_unfiltered_call(
    client: TestClient, factory: MagicMock
) -> None:
    """Omitting from keeps the current call; cinema and language stay ignored."""
    factory.movies.get_movie_screenings_query.execute.return_value = SimpleNamespace(
        movie_id="mov-1", movie_title="The Odyssey", screenings=[], total=0
    )

    response = client.get(
        "/v1/movies/mov-1/screenings",
        params={"cinema_id": "cin-1", "language": "V.O."},
    )

    assert response.status_code == 200
    factory.movies.get_movie_screenings_query.execute.assert_awaited_once_with(
        GetMovieScreeningsQuery.InputData(movie_id="mov-1", page=1, size=50)
    )


def test_get_movie_screenings_passes_from_as_start(
    client: TestClient, factory: MagicMock
) -> None:
    """The from query parameter is parsed and passed to the query as start."""
    factory.movies.get_movie_screenings_query.execute.return_value = SimpleNamespace(
        movie_id="mov-1", movie_title="The Odyssey", screenings=[], total=0
    )

    response = client.get(
        "/v1/movies/mov-1/screenings",
        params={"from": "2026-06-27T18:00:00+00:00", "page": 1, "size": 100},
    )

    assert response.status_code == 200
    factory.movies.get_movie_screenings_query.execute.assert_awaited_once_with(
        GetMovieScreeningsQuery.InputData(
            movie_id="mov-1",
            start=datetime(2026, 6, 27, 18, 0, tzinfo=UTC),
            page=1,
            size=100,
        )
    )


def test_get_movie_screenings_preserves_opaque_slash_id(
    client: TestClient, factory: MagicMock
) -> None:
    """An encoded slash in the movie ID reaches the query as the exact ID."""
    factory.movies.get_movie_screenings_query.execute.return_value = SimpleNamespace(
        movie_id="catalogue/id", movie_title="Slash film", screenings=[], total=0
    )

    response = client.get(
        "/v1/movies/catalogue%2Fid/screenings"
        "?from=2026-06-27T18%3A00%3A00%2B00%3A00&page=1&size=100"
    )

    assert response.status_code == 200
    factory.movies.get_movie_screenings_query.execute.assert_awaited_once_with(
        GetMovieScreeningsQuery.InputData(
            movie_id="catalogue/id",
            start=datetime(2026, 6, 27, 18, 0, tzinfo=UTC),
            page=1,
            size=100,
        )
    )


def test_get_movie_screenings_not_found(client: TestClient, factory: MagicMock) -> None:
    """GET /movies/{id}/screenings returns a 404 envelope for a missing movie."""
    factory.movies.get_movie_screenings_query.execute.side_effect = MovieNotFoundError(
        "A movie with ID 'missing' was not found"
    )

    response = client.get("/v1/movies/missing/screenings")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "not_found"


def test_get_cinema_movies(client: TestClient, factory: MagicMock) -> None:
    """GET /cinemas/{id}/movies returns the cinema's distinct movies."""
    factory.cinemas.get_cinema_movies_use_case.execute.return_value = SimpleNamespace(
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
        params={"from": "2026-06-27T00:00:00Z", "to": "2026-06-28T00:00:00Z"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["items"][0]["title"] == "The Odyssey"
    assert body["total"] == 1

    factory.cinemas.get_cinema_movies_use_case.execute.assert_awaited_once_with(
        GetCinemaMoviesUseCase.InputData(
            cinema_id="cin-1",
            start_date=datetime(2026, 6, 27, tzinfo=UTC),
            end_date=datetime(2026, 6, 28, tzinfo=UTC),
            page=1,
            size=50,
        )
    )


def test_get_cinema_movies_not_found(client: TestClient, factory: MagicMock) -> None:
    """GET /cinemas/{id}/movies returns a 404 envelope for an unknown cinema."""
    factory.cinemas.get_cinema_movies_use_case.execute.side_effect = (
        CinemaNotFoundError("A cinema with ID 'missing' was not found")
    )

    response = client.get("/v1/cinemas/missing/movies")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "not_found"


def test_get_cinema_movies_pagination(client: TestClient, factory: MagicMock) -> None:
    """The router forwards page/size and reports the use case's total."""
    factory.cinemas.get_cinema_movies_use_case.execute.return_value = SimpleNamespace(
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


def test_screening_movies_page_and_validation(
    client: TestClient, factory: MagicMock
) -> None:
    """Movie-first reads return terminal metadata and validate before querying."""
    query = create_autospec(BrowseScreeningMoviesQuery, instance=True)
    factory.screenings.browse_screening_movies_query = query
    query.execute.return_value = BrowseScreeningMoviesQuery.OutputData(
        movies=(), total=25
    )
    response = client.post(
        "/v1/screening-movies?start=2026-11-01&end=2026-11-01&page=2",
        json={},
    )
    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "page": 2,
        "size": 24,
        "pages": 2,
        "total": 25,
    }
    query.execute.assert_awaited_once_with(
        BrowseScreeningMoviesQuery.InputData(date(2026, 11, 1), date(2026, 11, 1), 2)
    )
    query.execute.reset_mock()
    for params in [
        "start=bad&end=2026-11-01",
        "start=2026-11-02&end=2026-11-01",
        "start=2026-11-01&end=2026-11-01&page=0",
    ]:
        assert client.post(f"/v1/screening-movies?{params}", json={}).status_code == 422
    query.execute.assert_not_awaited()


def test_screening_movies_inverted_range_returns_the_validation_envelope(
    client: TestClient, factory: MagicMock
) -> None:
    """An inverted browse range fails params validation, like day counts."""
    query = create_autospec(BrowseScreeningMoviesQuery, instance=True)
    factory.browse_screening_movies_query = query
    response = client.post(
        "/v1/screening-movies?start=2026-11-02&end=2026-11-01", json={}
    )
    assert response.status_code == 422
    body = response.json()
    body.pop("request_id")
    assert body == {
        "detail": "Request validation failed",
        "error_code": "invalid_input",
    }
    query.execute.assert_not_awaited()


def test_screening_movies_filters_reach_the_query(
    client: TestClient, factory: MagicMock
) -> None:
    """Repeated filters, one hour range and exclusions reach one movie-first query."""
    query = create_autospec(BrowseScreeningMoviesQuery, instance=True)
    factory.screenings.browse_screening_movies_query = query
    query.execute.return_value = BrowseScreeningMoviesQuery.OutputData(
        movies=(), total=0
    )
    response = client.post(
        "/v1/screening-movies?start=2026-11-01&end=2026-11-05&page=1"
        "&title=Dune&cinema=c1&cinema=c2&language=VO&language=VOSTF"
        "&exclude_cinema=c3&exclude_cinema=c4",
        json={"hours": {"operator": "is", "ranges": [{"start": 17, "end": 21}]}},
    )
    assert response.status_code == 200
    query.execute.assert_awaited_once_with(
        BrowseScreeningMoviesQuery.InputData(
            start=date(2026, 11, 1),
            end=date(2026, 11, 5),
            page=1,
            title="Dune",
            cinemas=("c1", "c2"),
            languages=("VO", "VOSTF"),
            hours=BrowseScreeningMoviesQuery.HourFilterInput(
                ranges=(BrowseScreeningMoviesQuery.HourRangeInput(start=17, end=21),)
            ),
            excluded_cinemas=("c3", "c4"),
        )
    )


def test_screening_movies_accepts_an_hour_filter_with_several_ranges(
    client: TestClient, factory: MagicMock
) -> None:
    """A structured hour filter keeps several ranges matched with OR."""
    query = create_autospec(BrowseScreeningMoviesQuery, instance=True)
    factory.screenings.browse_screening_movies_query = query
    query.execute.return_value = BrowseScreeningMoviesQuery.OutputData(
        movies=(), total=0
    )
    response = client.post(
        "/v1/screening-movies?start=2026-11-01",
        json={
            "hours": {
                "operator": "is",
                "ranges": [{"start": 0, "end": 17}, {"start": 21, "end": 24}],
            }
        },
    )
    assert response.status_code == 200
    query.execute.assert_awaited_once_with(
        BrowseScreeningMoviesQuery.InputData(
            start=date(2026, 11, 1),
            end=None,
            hours=BrowseScreeningMoviesQuery.HourFilterInput(
                ranges=(
                    BrowseScreeningMoviesQuery.HourRangeInput(start=0, end=17),
                    BrowseScreeningMoviesQuery.HourRangeInput(start=21, end=24),
                )
            ),
        )
    )


def test_screening_movies_maps_a_negative_hour_filter(
    client: TestClient, factory: MagicMock
) -> None:
    """A negative hour filter reaches the query without client complements."""
    query = create_autospec(BrowseScreeningMoviesQuery, instance=True)
    factory.screenings.browse_screening_movies_query = query
    query.execute.return_value = BrowseScreeningMoviesQuery.OutputData(
        movies=(), total=0
    )
    response = client.post(
        "/v1/screening-movies?start=2026-11-01",
        json={
            "hours": {
                "operator": "is_not",
                "ranges": [{"start": 17, "end": 21}],
            }
        },
    )
    assert response.status_code == 200
    query.execute.assert_awaited_once_with(
        BrowseScreeningMoviesQuery.InputData(
            start=date(2026, 11, 1),
            end=None,
            hours=BrowseScreeningMoviesQuery.HourFilterInput(
                ranges=(BrowseScreeningMoviesQuery.HourRangeInput(start=17, end=21),),
                excluded=True,
            ),
        )
    )


@pytest.mark.parametrize(
    "hours",
    [
        {"operator": "is", "ranges": []},
        {"operator": "is", "ranges": [{"start": 21, "end": 17}]},
        {"operator": "is", "ranges": [{"start": 17, "end": 17}]},
        {"operator": "is", "ranges": [{"start": -1, "end": 5}]},
        {"operator": "is", "ranges": [{"start": 0, "end": 25}]},
        {"operator": "is", "ranges": [{"start": "5", "end": 9}]},
        {"operator": "contains", "ranges": [{"start": 5, "end": 9}]},
    ],
)
def test_screening_movies_rejects_invalid_hour_ranges(
    client: TestClient, factory: MagicMock, hours: dict
) -> None:
    """Invalid operators and ranges fail Pydantic validation before querying."""
    query = create_autospec(BrowseScreeningMoviesQuery, instance=True)
    factory.screenings.browse_screening_movies_query = query
    response = client.post(
        "/v1/screening-movies?start=2026-11-01",
        json={"hours": hours},
    )
    assert response.status_code == 422
    query.execute.assert_not_awaited()


def test_screening_movie_metadata_and_preview_response(
    client: TestClient, factory: MagicMock
) -> None:
    """Card metadata, source language and the original booking URL reach delivery."""
    query = create_autospec(BrowseScreeningMoviesQuery, instance=True)
    factory.screenings.browse_screening_movies_query = query
    query.execute.return_value = SimpleNamespace(
        movies=[
            SimpleNamespace(
                id="film",
                title="Film",
                release_year=2026,
                directors=("Director",),
                duration_minutes=90,
                description=None,
                poster_url="https://posters.example/film.jpg",
                tmdb_rating=8.1,
                tmdb_vote_count=1234,
                screenings=[
                    SimpleNamespace(
                        id="show",
                        movie_id="film",
                        movie_title="Film",
                        cinema_id="cinema",
                        cinema_name="Cinema",
                        showtime=datetime.fromisoformat("2026-11-01T23:00:00+00:00"),
                        ticket_url="https://tickets.example/original",
                        room=None,
                        language="VOSTF",
                    )
                ],
            )
        ],
        total=1,
    )
    data = client.post(
        "/v1/screening-movies?start=2026-11-01&end=2026-11-01", json={}
    ).json()
    assert data["total"] == 1 and data["pages"] == 1
    assert data["items"][0]["directors"] == ["Director"]
    assert data["items"][0]["tmdb_rating"] == 8.1
    assert data["items"][0]["tmdb_vote_count"] == 1234
    assert data["items"][0]["screenings"][0]["language"] == "VOSTF"
    assert (
        data["items"][0]["screenings"][0]["ticket_url"]
        == "https://tickets.example/original"
    )


def _day_count(day: date, screenings: int) -> SimpleNamespace:
    return SimpleNamespace(date=day, screenings=screenings)


def test_screening_day_counts_return_every_day_and_reach_the_query(
    client: TestClient, factory: MagicMock
) -> None:
    """One request carries every filter and returns each day's total, zeros too."""
    query = create_autospec(CountScreeningDaysQuery, instance=True)
    factory.screenings.count_screening_days_query = query
    query.execute.return_value = SimpleNamespace(
        days=(_day_count(date(2026, 11, 1), 0), _day_count(date(2026, 11, 2), 7))
    )
    response = client.post(
        "/v1/screening-day-counts?start=2026-11-01&end=2026-11-02"
        "&title=Dune&cinema=c1&language=VO&exclude_cinema=c3",
        json={
            "hours": {
                "operator": "is_not",
                "ranges": [{"start": 0, "end": 17}, {"start": 21, "end": 24}],
            }
        },
    )
    assert response.status_code == 200
    assert response.json() == {
        "days": [
            {"date": "2026-11-01", "screenings": 0},
            {"date": "2026-11-02", "screenings": 7},
        ]
    }
    query.execute.assert_awaited_once_with(
        CountScreeningDaysQuery.InputData(
            start=date(2026, 11, 1),
            end=date(2026, 11, 2),
            title="Dune",
            cinemas=("c1",),
            languages=("VO",),
            hours=CountScreeningDaysQuery.HourFilterInput(
                ranges=(
                    CountScreeningDaysQuery.HourRangeInput(start=0, end=17),
                    CountScreeningDaysQuery.HourRangeInput(start=21, end=24),
                ),
                excluded=True,
            ),
            excluded_cinemas=("c3",),
        )
    )


@pytest.mark.parametrize(
    "params,body",
    [
        ("start=2026-11-01", {}),
        ("start=bad&end=2026-11-01", {}),
        ("start=2026-11-02&end=2026-11-01", {}),
        (
            "start=2026-11-01&end=2026-11-01",
            {"hours": {"operator": "is", "ranges": [{"start": 21, "end": 17}]}},
        ),
    ],
)
def test_screening_day_counts_reject_invalid_ranges_before_querying(
    client: TestClient, factory: MagicMock, params: str, body: dict
) -> None:
    """A missing, malformed or inverted horizon, or a bad hour range, is a 422."""
    query = create_autospec(CountScreeningDaysQuery, instance=True)
    factory.screenings.count_screening_days_query = query
    response = client.post(f"/v1/screening-day-counts?{params}", json=body)
    assert response.status_code == 422
    query.execute.assert_not_awaited()


def test_screening_day_counts_map_an_oversized_horizon_to_422(
    client: TestClient, factory: MagicMock
) -> None:
    """The query's horizon limit reaches clients as invalid input."""
    query = create_autospec(CountScreeningDaysQuery, instance=True)
    factory.screenings.count_screening_days_query = query
    query.execute.side_effect = TooManyScreeningDaysError("too many days")
    response = client.post(
        "/v1/screening-day-counts?start=2026-11-01&end=2026-12-31", json={}
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "invalid_input"


def test_list_movies_preserves_opaque_slash_id(
    client: TestClient, factory: MagicMock
) -> None:
    """The one-ID query preserves slashes that cannot survive route matching."""
    factory.movies.list_movies_use_case.execute.return_value = SimpleNamespace(
        movies=[], total=0
    )
    response = client.get("/v1/movies?ids=catalogue%2Fid&page=1&size=1")
    assert response.status_code == 200
    factory.movies.list_movies_use_case.execute.assert_awaited_once_with(
        ListMoviesUseCase.InputData(ids=("catalogue/id",), page=1, size=1)
    )
