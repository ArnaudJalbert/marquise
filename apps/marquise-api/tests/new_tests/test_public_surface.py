"""The API only reads the catalog: no tokens, no screening mutations."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest
from fastapi.testclient import TestClient

from marquise import (
    BrowseScreeningMoviesQuery,
    MarquiseFactory,
    SearchScreeningsQuery,
)
from marquise_api.app import create_app


@pytest.fixture
def factory() -> MarquiseFactory:
    """Provide a factory whose screening queries find nothing."""
    fake = create_autospec(MarquiseFactory, instance=True)
    fake.search_screenings_query = create_autospec(SearchScreeningsQuery, instance=True)
    fake.search_screenings_query.execute.return_value = (
        SearchScreeningsQuery.OutputData(screenings=[], total=0)
    )
    fake.browse_screening_movies_query = create_autospec(
        BrowseScreeningMoviesQuery, instance=True
    )
    fake.browse_screening_movies_query.execute.return_value = (
        BrowseScreeningMoviesQuery.OutputData(movies=(), total=0)
    )
    return fake


@pytest.fixture
def client(factory: MarquiseFactory) -> TestClient:
    """Provide a client for the app built on the fake factory."""
    return TestClient(create_app(factory=factory))


def test_get_query_without_token_returns_empty_page(client: TestClient) -> None:
    """An anonymous screening search with no matches returns an empty page."""
    response = client.get("/v1/screenings")

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


def test_post_query_without_token_returns_empty_page(client: TestClient) -> None:
    """An anonymous POST screening-movie query with no matches returns no movies."""
    response = client.post("/v1/screening-movies?start=2026-11-01", json={})

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total"] == 0


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", "/v1/screenings"),
        ("PATCH", "/v1/screenings/screening-1"),
        ("DELETE", "/v1/screenings/screening-1"),
    ],
)
def test_screening_mutation_methods_are_not_allowed(
    client: TestClient, method: str, path: str
) -> None:
    """Screening routes still answer queries but reject create, edit and delete."""
    response = client.request(
        method,
        path,
        json={},
        headers={"Authorization": "Bearer token", "Idempotency-Key": "key"},
    )

    assert response.status_code == 405
    assert response.json()["error_code"] == "method_not_allowed"


def test_openapi_lists_no_auth_or_screening_mutations(client: TestClient) -> None:
    """The schema documents no security scheme and no screening mutation."""
    schema = client.get("/openapi.json").json()

    assert "securitySchemes" not in schema.get("components", {})
    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            assert "security" not in operation, (method, path)
            assert not {"401", "403"} & set(operation["responses"]), (method, path)
        if path.startswith("/v1/screenings"):
            assert set(operations) == {"get"}, path
