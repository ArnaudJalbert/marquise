"""Concrete showtime source registry wiring."""

from __future__ import annotations

from marquise.infrastructure.sources.cinemacinema import CinemaCinemaSource
from marquise.infrastructure.sources.cinemamoderne import CinemaModerneSource
from marquise.infrastructure.sources.cinemapublic import CinemaPublicSource
from marquise.infrastructure.sources.cinematheque import CinemathequeSource
from marquise.infrastructure.sources.cineplex import CineplexSource
from marquise.infrastructure.sources.cinestarz import CineStarzSource
from marquise.infrastructure.sources.outremont import OutremontSource
from marquise.interface_adapters.repositories.source_adapters.cinemacinema import (
    CinemaCinemaAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.cinemamoderne import (
    CinemaModerneAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.cinemapublic import (
    CinemaPublicAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.cinematheque import (
    CinemathequeAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.cineplex import (
    CineplexAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.cinestarz import (
    CineStarzAdapter,
)
from marquise.interface_adapters.repositories.source_adapters.outremont import (
    OutremontAdapter,
)
from marquise.interface_adapters.repositories.source_registry import SourceRegistry


def build_source_registry() -> SourceRegistry:
    """Build registry containing every configured showtime source."""
    registry = SourceRegistry()
    registry.register("cinemacinema", CinemaCinemaAdapter(CinemaCinemaSource()))
    registry.register("cinemamoderne", CinemaModerneAdapter(CinemaModerneSource()))
    registry.register("cinemapublic", CinemaPublicAdapter(CinemaPublicSource()))
    registry.register("cinestarz", CineStarzAdapter(CineStarzSource()))
    registry.register("cinematheque", CinemathequeAdapter(CinemathequeSource()))
    registry.register("cineplex", CineplexAdapter(CineplexSource()))
    registry.register("outremont", OutremontAdapter(OutremontSource()))
    return registry
