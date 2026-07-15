"""Tests for OpenAPI schema generation and documentation metadata."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from fastapi_cache.backends.inmemory import InMemoryBackend

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
def client() -> TestClient:
    """Provide a TestClient backed by a fake container."""
    return TestClient(create_app(factory=MagicMock()))


def test_openapi_schema_generation_succeeds(client: TestClient) -> None:
    """GET /openapi.json succeeds and is valid JSON."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Marquise API"


def test_openapi_description_documents_no_auth(client: TestClient) -> None:
    """The top-level description mentions there is no authentication."""
    schema = client.get("/openapi.json").json()

    assert "Authentication" in schema["info"]["description"]
    assert "None" in schema["info"]["description"]


@pytest.mark.parametrize(
    ("path", "expected_status_codes"),
    [
        ("/v1/cinemas", {"422", "429"}),
        ("/v1/cinemas/{cinema_id}", {"404", "422", "429"}),
        ("/v1/cinemas/{cinema_id}/screenings", {"404", "422", "429"}),
        ("/v1/cinemas/{cinema_id}/movies", {"404", "422", "429"}),
        ("/v1/movies", {"422", "429"}),
        ("/v1/movies/{movie_id}", {"404", "422", "429"}),
        ("/v1/movies/{movie_id}/screenings", {"404", "422", "429"}),
        ("/v1/screenings", {"422", "429"}),
        ("/v1/screenings/{screening_id}", {"404", "422", "429"}),
    ],
)
def test_endpoint_documents_error_responses(
    client: TestClient, path: str, expected_status_codes: set[str]
) -> None:
    """Each documented endpoint's OpenAPI responses include its error codes."""
    schema = client.get("/openapi.json").json()

    documented = schema["paths"][path]["get"]["responses"]

    assert expected_status_codes <= set(documented.keys())


def test_ready_documents_503_with_ad_hoc_body(client: TestClient) -> None:
    """/ready's 503 response documents the ad hoc {"status": ...} body."""
    schema = client.get("/openapi.json").json()

    responses = schema["paths"]["/ready"]["get"]["responses"]

    assert "503" in responses


def test_cinema_response_schema_includes_example(client: TestClient) -> None:
    """CinemaResponse's generated schema includes the configured example."""
    schema = client.get("/openapi.json").json()

    cinema_schema = schema["components"]["schemas"]["CinemaResponse"]

    assert "examples" in cinema_schema
