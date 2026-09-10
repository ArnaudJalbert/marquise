"""Transport policy for authentication endpoints."""

from __future__ import annotations

from http.client import HTTPMessage
from ipaddress import ip_address
from typing import IO
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request

from marquise.interface_adapters.exceptions.auth import AuthGatewayError


def validate_auth_url(url: str, *, allow_insecure_local_http: bool = False) -> str:
    """Require HTTPS, with an explicit literal-loopback HTTP development opt-in."""
    try:
        if any(character.isspace() or ord(character) < 32 for character in url):
            raise ValueError
        parsed = urlsplit(url)
        if (
            not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or "\\" in url
        ):
            raise ValueError
        _ = parsed.port  # Reject malformed/out-of-range ports before network I/O.
        if parsed.scheme == "https":
            return url.rstrip("/")
        if (
            allow_insecure_local_http
            and parsed.scheme == "http"
            and ip_address(parsed.hostname).is_loopback
        ):
            return url.rstrip("/")
    except ValueError:
        pass
    raise ValueError(
        "Authentication URL must use HTTPS; development HTTP requires "
        "explicit opt-in and a literal loopback IP"
    )


class RejectAuthRedirects(HTTPRedirectHandler):
    """Never forward authentication credentials to a redirect destination."""

    def redirect_request(
        self,
        req: Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: HTTPMessage,
        newurl: str,
    ) -> None:
        """Fail closed on redirects, including same-origin redirects."""
        raise AuthGatewayError("Authentication endpoint redirects are not allowed")
