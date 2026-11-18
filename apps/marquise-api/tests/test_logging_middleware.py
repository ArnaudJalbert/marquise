"""Tests for structured JSON request logging."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import MagicMock, create_autospec

import pytest
from fastapi.testclient import TestClient

from marquise import (
    CinemaUseCases,
    GetCinemaUseCase,
    GetMovieUseCase,
    ListCinemasUseCase,
    MarquiseFactory,
    MovieNotFoundError,
    MovieUseCases,
)
from marquise_api.logging_middleware import (
    JsonFormatter,
    configure_logging,
)


def _make_record(**kwargs: object) -> logging.LogRecord:
    """Build a LogRecord with sensible defaults, overridable via kwargs."""
    defaults: dict[str, object] = {
        "name": "marquise.test",
        "level": logging.INFO,
        "pathname": __file__,
        "lineno": 1,
        "msg": "request completed",
        "args": (),
        "exc_info": None,
    }
    defaults.update(kwargs)
    return logging.LogRecord(**defaults)  # type: ignore[arg-type]


def test_json_formatter_produces_valid_json_with_expected_keys() -> None:
    """A plain log record formats to JSON with the core envelope fields."""
    record = _make_record()
    record.request_id = "req-1"
    record.status_code = 200

    formatted = json.loads(JsonFormatter().format(record))

    assert formatted["message"] == "request completed"
    assert formatted["level"] == "INFO"
    assert formatted["logger"] == "marquise.test"
    assert formatted["request_id"] == "req-1"
    assert formatted["status_code"] == 200
    assert "timestamp" in formatted


def test_json_formatter_includes_traceback_for_exception_records() -> None:
    """A record with exc_info includes a formatted traceback."""
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = _make_record(exc_info=sys.exc_info())

    formatted = json.loads(JsonFormatter().format(record))

    assert "ValueError: boom" in formatted["exc_info"]


def test_configure_logging_is_idempotent() -> None:
    """Calling configure_logging() twice does not stack duplicate handlers."""
    configure_logging()
    configure_logging()

    assert len(logging.getLogger().handlers) == 1


@pytest.fixture
def factory() -> MagicMock:
    """Provide fake factory with autospecced read use cases."""
    fake = create_autospec(MarquiseFactory, instance=True)
    fake.cinemas = create_autospec(CinemaUseCases, instance=True)
    fake.cinemas.list_cinemas_use_case = create_autospec(
        ListCinemasUseCase, instance=True
    )
    fake.cinemas.list_cinemas_use_case.execute.return_value = SimpleNamespace(
        cinemas=[], total=0
    )
    fake.cinemas.get_cinema_use_case = create_autospec(GetCinemaUseCase, instance=True)
    fake.movies = create_autospec(MovieUseCases, instance=True)
    fake.movies.get_movie_use_case = create_autospec(GetMovieUseCase, instance=True)
    return fake


@pytest.fixture
def client(factory: MagicMock, client_opener: Callable[..., TestClient]) -> TestClient:
    """Provide a TestClient backed by the fake container."""
    return client_opener(factory)


def test_incoming_request_id_header_is_echoed_back(client: TestClient) -> None:
    """A client-supplied X-Request-ID is reused rather than replaced."""
    response = client.get("/health", headers={"X-Request-ID": "client-supplied-id"})

    assert response.headers["X-Request-ID"] == "client-supplied-id"


def test_missing_request_id_header_generates_a_uuid(client: TestClient) -> None:
    """Omitting X-Request-ID results in a generated UUID-shaped value."""
    response = client.get("/health")

    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 36
    assert request_id.count("-") == 4


def test_each_request_logs_one_structured_line(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """Each request produces one log record with method/path/status/duration."""
    with caplog.at_level(logging.INFO, logger="marquise_api.logging_middleware"):
        response = client.get("/health")

    matching = [r for r in caplog.records if getattr(r, "path", None) == "/health"]
    assert len(matching) == 1
    record = matching[0]
    assert record.method == "GET"
    assert record.status_code == 200
    assert record.request_id == response.headers["X-Request-ID"]
    assert isinstance(record.duration_ms, float)


def test_error_response_request_id_matches_header(
    client: TestClient, factory: MagicMock
) -> None:
    """An error envelope's request_id matches the X-Request-ID response header."""
    factory.movies.get_movie_use_case.execute.side_effect = MovieNotFoundError("nope")

    response = client.get("/v1/movies/missing")

    assert response.status_code == 404
    assert response.json()["request_id"] == response.headers["X-Request-ID"]
