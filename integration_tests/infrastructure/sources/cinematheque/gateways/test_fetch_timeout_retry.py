"""Schedule fetch timeout regressions against a real local HTTP server."""

from __future__ import annotations

import ssl
import threading
import time
import urllib.request
from collections.abc import Iterator
from http.client import HTTPResponse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import create_autospec

import pytest

from marquise.infrastructure.sources.cinematheque.gateways import source

_TEST_TIMEOUT_SECONDS = 0.1
_STALL_SECONDS = 0.5


@pytest.fixture
def schedule_server(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[list[bool], list[str]]]:
    """Serve an empty schedule page, stalling the requests marked to stall."""
    stalls: list[bool] = []
    requests: list[str] = []
    monkeypatch.setattr(time, "sleep", create_autospec(time.sleep))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            """Stall past the client timeout when configured, else respond."""
            requests.append(self.path)
            if stalls[min(len(requests) - 1, len(stalls) - 1)]:
                threading.Event().wait(_STALL_SECONDS)
            body = b"<html><body></body></html>"
            try:
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except BrokenPipeError:
                pass  # The client already gave up on this stalled request.

        def log_message(self, format: str, *args: str) -> None:
            """Suppress local server logs."""

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    original_urlopen = urllib.request.urlopen

    def short_timeout_urlopen(
        request: urllib.request.Request, *, context: ssl.SSLContext, timeout: float
    ) -> HTTPResponse:
        return original_urlopen(request, context=context, timeout=_TEST_TIMEOUT_SECONDS)

    monkeypatch.setattr(urllib.request, "urlopen", short_timeout_urlopen)
    monkeypatch.setattr(source, "BASE_URL", f"http://127.0.0.1:{server.server_port}/")
    try:
        yield stalls, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_schedule_recovers_from_transient_read_timeout(
    schedule_server: tuple[list[bool], list[str]],
) -> None:
    """A slow schedule page is fetched again instead of failing the import."""
    stalls, requests = schedule_server
    stalls.extend([True, True, False])

    assert source.fetch_showtimes() == []
    assert len(requests) == 3
    assert len(set(requests)) == 1


def test_schedule_read_timeout_fails_after_three_attempts(
    schedule_server: tuple[list[bool], list[str]],
) -> None:
    """A page that never answers in time still fails, after three attempts."""
    stalls, requests = schedule_server
    stalls.append(True)

    with pytest.raises(TimeoutError):
        source.fetch_showtimes()
    assert len(requests) == 3
