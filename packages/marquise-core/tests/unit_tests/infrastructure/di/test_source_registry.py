"""Tests for concrete source-registry wiring."""

from __future__ import annotations

from unittest.mock import patch

from marquise.infrastructure.di.source_registry import build_source_registry


def test_build_source_registry_registers_current_sources() -> None:
    """Registry wiring exposes every current source and configured Cineplex key."""
    with patch(
        "marquise.infrastructure.di.source_registry.CineplexSource"
    ) as cineplex_source:
        registry = build_source_registry("cineplex-key")

    assert set(registry.list_available()) == {
        "cinemacinema",
        "cinemamoderne",
        "cinemapublic",
        "cinestarz",
        "cinematheque",
        "cineplex",
        "outremont",
    }
    cineplex_source.assert_called_once_with(api_key="cineplex-key")
