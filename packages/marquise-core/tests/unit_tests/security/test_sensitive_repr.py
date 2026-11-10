"""Security checks for representations of credential-bearing values."""

from marquise.infrastructure.supabase.config import Settings


def test_sensitive_dataclass_reprs_do_not_include_credentials() -> None:
    """Configured secrets stay out of diagnostic reprs."""
    values = [
        Settings(
            database_url="postgresql://user:database-password@example.com/db",
            cineplex_api_key="cineplex-secret",
            supabase_url="https://project.supabase.co",
            supabase_publishable_key="publishable-secret",
            supabase_service_role_key="service-role-secret",
        ),
    ]

    rendered = repr(values)

    for secret in (
        "database-password",
        "cineplex-secret",
        "publishable-secret",
        "service-role-secret",
    ):
        assert secret not in rendered
