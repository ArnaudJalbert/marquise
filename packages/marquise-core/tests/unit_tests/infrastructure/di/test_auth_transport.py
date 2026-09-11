"""Pure authentication transport-policy and composition checks."""

import pytest

from marquise.infrastructure.auth.transport import validate_auth_url
from marquise.infrastructure.di.auth import build_verify_access_token_query


@pytest.mark.parametrize(
    "url",
    [
        "http://project.supabase.co",
        "http://127.0.0.1:54321",
        "ftp://example.com",
        "https://",
        "https://user:password@example.com",
        "https://example.com?token=secret",
        "https://example.com#fragment",
        "https://example.com:99999",
        "https://example.com\n",
    ],
)
def test_auth_url_rejects_unsafe_configuration(url: str) -> None:
    """Unsafe endpoint settings fail before any credentials can be sent."""
    with pytest.raises(ValueError):
        validate_auth_url(url)


@pytest.mark.parametrize("host", ["127.0.0.1", "[::1]"])
def test_development_opt_in_accepts_literal_loopback(host: str) -> None:
    """Development HTTP needs both explicit opt-in and a loopback address."""
    url = f"http://{host}:54321"
    assert validate_auth_url(url, allow_insecure_local_http=True) == url


@pytest.mark.parametrize(
    "host", ["localhost", "example.com", "10.0.0.1", "127.0.0.1.example.com"]
)
def test_development_opt_in_does_not_allow_remote_http(host: str) -> None:
    """The development flag cannot allow cleartext credentials to remote hosts."""
    with pytest.raises(ValueError):
        validate_auth_url(f"http://{host}", allow_insecure_local_http=True)


def test_https_url_is_accepted() -> None:
    """Production HTTPS works without a development override."""
    assert (
        validate_auth_url("https://project.supabase.co/")
        == "https://project.supabase.co"
    )


def test_jwks_composition_checks_https(monkeypatch: pytest.MonkeyPatch) -> None:
    """The token-verification path enforces the same configured URL policy."""
    monkeypatch.delenv("MARQUISE_AUTH_ALLOW_LOCAL_HTTP", raising=False)
    with pytest.raises(ValueError):
        build_verify_access_token_query("http://127.0.0.1:54321")
    monkeypatch.setenv("MARQUISE_AUTH_ALLOW_LOCAL_HTTP", "1")
    assert build_verify_access_token_query("http://127.0.0.1:54321") is not None
