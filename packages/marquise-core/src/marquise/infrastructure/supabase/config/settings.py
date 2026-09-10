"""Application settings."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Settings:
    """Application configuration loaded from environment variables.

    Attributes:
        database_url: Full PostgreSQL connection string used by asyncpg.
        schema: Database schema for all tables (default ``"marquise"``).
        cineplex_api_key: API key for the Cineplex theatrical API.
    """

    database_url: str = field(default="", repr=False)
    cineplex_api_key: str = field(default="", repr=False)
    schema: str = "marquise"
    supabase_url: str = ""
    supabase_publishable_key: str = field(default="", repr=False)
    supabase_service_role_key: str = field(default="", repr=False)
