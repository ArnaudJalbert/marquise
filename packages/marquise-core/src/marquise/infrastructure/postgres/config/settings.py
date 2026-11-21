"""Application settings."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Settings:
    """Application configuration loaded from environment variables.

    Attributes:
        database_url: Full PostgreSQL connection string used by asyncpg.
        tmdb_api_key: API key for TMDB movie metadata.
        schema: Database schema for all tables.
    """

    database_url: str = field(repr=False)
    tmdb_api_key: str = field(repr=False)
    schema: str
