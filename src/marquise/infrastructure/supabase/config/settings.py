"""Application settings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    """Application configuration loaded from environment variables.

    Attributes:
        database_url: Full PostgreSQL connection string used by asyncpg.
    """

    database_url: str
