"""Loopback HTTP transport for offline source integration tests."""

from __future__ import annotations

import ssl
import threading
import urllib.request
from collections.abc import Iterator
from http.client import HTTPResponse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

import pytest


@pytest.fixture
def local_http(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[str, dict[str, tuple[bytes, str]], list[tuple[str, str | None]]]]:
    """Serve responses locally and reject accidental outbound provider calls."""
    routes: dict[str, tuple[bytes, str]] = {}
    requests: list[tuple[str, str | None]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            requests.append((self.path, self.headers.get("Ocp-Apim-Subscription-Key")))
            response = routes.get(self.path)
            if response is None:
                self.send_error(404)
                return
            body, content_type = response
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: str) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    original_urlopen = urllib.request.urlopen

    def loopback_only(
        request: urllib.request.Request, *, context: ssl.SSLContext, timeout: float
    ) -> HTTPResponse:
        assert urlsplit(request.full_url).hostname == "127.0.0.1", request.full_url
        return original_urlopen(request, context=context, timeout=timeout)

    monkeypatch.setattr(urllib.request, "urlopen", loopback_only)
    try:
        yield f"http://127.0.0.1:{server.server_port}", routes, requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
