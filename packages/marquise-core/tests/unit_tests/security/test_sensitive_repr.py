"""Security checks for representations of credential-bearing values."""

from marquise.application.queries.verify_access_token import VerifyAccessTokenQuery
from marquise.application.use_cases.auth import (
    AuthenticateAdministratorUseCase,
    InviteAccountUseCase,
    SetAccountRoleUseCase,
)
from marquise.infrastructure.supabase.config import Settings


def test_sensitive_dataclass_reprs_do_not_include_credentials() -> None:
    """Passwords, tokens, and configured secrets stay out of diagnostic reprs."""
    values = [
        AuthenticateAdministratorUseCase.InputData(
            email="admin@example.com", password="administrator-password"
        ),
        InviteAccountUseCase.InputData(
            administrator_email="admin@example.com",
            administrator_password="administrator-password",
            email="user@example.com",
            role="member",
        ),
        SetAccountRoleUseCase.InputData(
            administrator_email="admin@example.com",
            administrator_password="administrator-password",
            email="user@example.com",
            role="editor",
        ),
        VerifyAccessTokenQuery.InputData(token="eyJ.sensitive.access-token"),
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
        "administrator-password",
        "eyJ.sensitive.access-token",
        "database-password",
        "cineplex-secret",
        "publishable-secret",
        "service-role-secret",
    ):
        assert secret not in rendered
