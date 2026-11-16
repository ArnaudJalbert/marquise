"""Schedule fetch timeout regressions against a real local HTTP server."""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock, call, create_autospec

import pytest

from marquise.infrastructure.sources.cinematheque.gateways import source

_STALL_SECONDS = 0.5


@pytest.fixture
def schedule_server(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[list[bool], list[str], Mock]]:
    """Serve an empty schedule page, stalling the requests marked to stall."""
    stalls: list[bool] = []
    requests: list[str] = []
    sleep = create_autospec(time.sleep)
    monkeypatch.setattr(time, "sleep", sleep)

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
    monkeypatch.setattr(source, "_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(source, "BASE_URL", f"http://127.0.0.1:{server.server_port}/")
    try:
        yield stalls, requests, sleep
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_schedule_recovers_from_transient_read_timeout(
    schedule_server: tuple[list[bool], list[str], Mock],
) -> None:
    """A slow schedule page is fetched again instead of failing the import."""
    stalls, requests, sleep = schedule_server
    stalls.extend([True, True, False])

    assert source.fetch_showtimes() == []
    assert requests == [requests[0]] * 3
    assert sleep.call_args_list == [call(0.5), call(1.0)]


def test_schedule_read_timeout_fails_after_three_attempts(
    schedule_server: tuple[list[bool], list[str], Mock],
) -> None:
    """A page that never answers in time still fails, after three attempts."""
    stalls, requests, _ = schedule_server
    stalls.append(True)

    with pytest.raises(TimeoutError):
        source.fetch_showtimes()
    assert requests == [requests[0]] * 3
