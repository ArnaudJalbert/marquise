"""Environment configuration for Supabase Auth admin operations."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthSettings:
    """Supabase Auth and role-store configuration."""

    supabase_url: str
    service_role_key: str
    database_url: str
    schema: str = "marquise"


def load_auth_settings() -> AuthSettings:
    """Load Auth admin settings from environment variables."""
    missing = [
        name
        for name, value in (
            ("SUPABASE_URL", os.environ.get("SUPABASE_URL")),
            ("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_SERVICE_ROLE_KEY")),
            ("DATABASE_URL", os.environ.get("DATABASE_URL")),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            f"Missing required environment variable(s): {', '.join(missing)}"
        )
    return AuthSettings(
        supabase_url=os.environ["SUPABASE_URL"].rstrip("/"),
        service_role_key=os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        database_url=os.environ["DATABASE_URL"],
        schema=os.environ.get("DATABASE_SCHEMA", "marquise"),
    )
