"""Tests for concrete source-registry wiring."""

from __future__ import annotations

from marquise.infrastructure.di.source_registry import build_source_registry


def test_build_source_registry_registers_current_sources() -> None:
    """Registry wiring exposes every current source."""
    registry = build_source_registry()

    assert set(registry.list_available()) == {
        "cinemacinema",
        "cinemamoderne",
        "cinemapublic",
        "cinestarz",
        "cinematheque",
        "cineplex",
        "outremont",
    }
