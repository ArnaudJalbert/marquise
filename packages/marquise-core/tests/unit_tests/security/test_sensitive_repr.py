"""Security checks for representations of credential-bearing values."""

from marquise.infrastructure.supabase.config import Settings


def test_sensitive_dataclass_reprs_do_not_include_credentials() -> None:
    """Configured secrets stay out of diagnostic reprs."""
    values = [
        Settings(
            database_url="postgresql://user:database-password@example.com/db",
            tmdb_api_key="tmdb-secret",
            schema="marquise",
        ),
    ]

    rendered = repr(values)

    for secret in (
        "database-password",
        "tmdb-secret",
    ):
        assert secret not in rendered
