"""Tests for concrete source-registry wiring."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from marquise.infrastructure.di.container import Container
from marquise.infrastructure.di.source_registry import build_source_registry
from marquise.interface_adapters.repositories.source_registry import SourceRegistry


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required container environment."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")


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


def test_container_caches_built_source_registry() -> None:
    """One container builds its source registry once and reuses same instance."""
    registry = SourceRegistry()
    with patch(
        "marquise.infrastructure.di.container.build_source_registry",
        return_value=registry,
    ) as build:
        container = Container()

        assert container._source_registry is registry
        assert container._source_registry is registry

    build.assert_called_once_with("")
