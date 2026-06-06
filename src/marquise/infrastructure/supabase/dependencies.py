"""Dependency injection wiring for Supabase."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from marquise.infrastructure.supabase.config import Settings


def get_settings() -> Settings:
    """Create a Settings instance from environment variables.

    Loads the ``.env`` file on first call, then reads ``DATABASE_URL``
    from the environment.

    Returns:
        A frozen Settings dataclass populated from the environment.

    Raises:
        KeyError: If the ``DATABASE_URL`` environment variable is not set.
    """
    load_dotenv()
    return Settings(database_url=os.environ["DATABASE_URL"])
