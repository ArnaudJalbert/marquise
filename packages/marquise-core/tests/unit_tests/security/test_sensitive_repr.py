"""Security checks for representations of credential-bearing values."""

from marquise.infrastructure.supabase.config import Settings


def test_sensitive_dataclass_reprs_do_not_include_credentials() -> None:
    """Configured secrets stay out of diagnostic reprs."""
    values = [
        Settings(
            database_url="postgresql://user:database-password@example.com/db",
            cineplex_api_key="cineplex-secret",
            tmdb_api_key="tmdb-secret",
        ),
    ]

    rendered = repr(values)

    for secret in (
        "database-password",
        "cineplex-secret",
        "tmdb-secret",
    ):
        assert secret not in rendered
