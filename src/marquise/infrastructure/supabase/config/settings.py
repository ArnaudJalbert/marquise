"""Application settings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Application configuration loaded from environment variables.

    Attributes:
        database_url: Full PostgreSQL connection string used by asyncpg.
        supabase_url: Supabase project URL for the auth client.
        supabase_publishable_key: Supabase publishable API key for the auth
            client.
    """

    database_url: str
    supabase_url: str
    supabase_publishable_key: str
