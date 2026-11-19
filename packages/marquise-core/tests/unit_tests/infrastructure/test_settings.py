"""Tests for the application settings."""

from __future__ import annotations

import pytest

from marquise.infrastructure.postgres.config import Settings


def test_settings_have_no_defaults() -> None:
    """Building settings without values fails instead of using defaults."""
    with pytest.raises(TypeError):
        Settings()  # type: ignore[call-arg]
