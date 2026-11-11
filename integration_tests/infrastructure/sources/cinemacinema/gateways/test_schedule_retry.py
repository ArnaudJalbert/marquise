"""Schedule retry regressions against a real local HTTP server."""

from __future__ import annotations

import threading
import urllib.error
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from marquise.infrastructure.sources.cinemacinema.gateways import source


@pytest.fixture
def schedule_server(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[list[int], list[str]]]:
    """Serve controlled HTTP responses without mocking network I/O."""
    statuses: list[int] = []
    requests: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            """Return the next configured status and a valid empty schedule."""
            requests.append(self.path)
            status = statuses[min(len(requests) - 1, len(statuses) - 1)]
            body = b'{"nodes": []}'
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: str) -> None:
            """Suppress local server logs."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    monkeypatch.setattr(
        source, "SCHEDULE_URL", f"http://127.0.0.1:{server.server_port}/schedule"
    )
    try:
        yield statuses, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.mark.parametrize("status", [502, 503, 504])
def test_schedule_recovers_from_transient_http_error(
    schedule_server: tuple[list[int], list[str]], status: int
) -> None:
    """A transient provider error retries the same date and returns parsed data."""
    statuses, requests = schedule_server
    statuses.extend([status, status, 200])

    assert source._fetch_schedule("2026-10-05") == {}
    assert requests == ["/schedule?date=2026-10-05"] * 3


@pytest.mark.parametrize("status", [502, 503, 504, 400, 401, 404, 429, 500])
def test_schedule_http_failure_remains_fatal(
    schedule_server: tuple[list[int], list[str]], status: int
) -> None:
    """Retries stop after three attempts; non-retryable errors fail immediately."""
    statuses, requests = schedule_server
    statuses.append(status)

    with pytest.raises(urllib.error.HTTPError) as raised:
        source._fetch_schedule()
    try:
        assert raised.value.code == status
        attempts = 3 if status in {502, 503, 504} else 1
        assert requests == ["/schedule"] * attempts
    finally:
        raised.value.close()


def test_successful_schedule_is_not_retried(
    schedule_server: tuple[list[int], list[str]],
) -> None:
    """A healthy schedule request returns without additional requests."""
    statuses, requests = schedule_server
    statuses.append(200)

    assert source._fetch_schedule() == {}
    assert requests == ["/schedule"]
