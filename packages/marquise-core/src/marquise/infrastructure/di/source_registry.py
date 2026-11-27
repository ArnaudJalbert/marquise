"""Concrete showtime source registry wiring."""

from __future__ import annotations

from marquise.infrastructure.sources.cinemacinema import CinemaCinemaSource
from marquise.infrastructure.sources.cinemamoderne import CinemaModerneSource
from marquise.infrastructure.sources.cinemapublic import CinemaPublicSource
from marquise.infrastructure.sources.cinematheque import CinemathequeSource
from marquise.infrastructure.sources.cineplex import CineplexSource
from marquise.infrastructure.sources.cinestarz import CineStarzSource
from marquise.infrastructure.sources.outremont import OutremontSource
from marquise.interface_adapters.sources.cinemacinema import (
    CinemaCinemaAdapter,
)
from marquise.interface_adapters.sources.cinemamoderne import (
    CinemaModerneAdapter,
)
from marquise.interface_adapters.sources.cinemapublic import (
    CinemaPublicAdapter,
)
from marquise.interface_adapters.sources.cinematheque import (
    CinemathequeAdapter,
)
from marquise.interface_adapters.sources.cineplex import (
    CineplexAdapter,
)
from marquise.interface_adapters.sources.cinestarz import (
    CineStarzAdapter,
)
from marquise.interface_adapters.sources.outremont import (
    OutremontAdapter,
)
from marquise.interface_adapters.sources.scraper_source_registry import (
    ScraperSourceRegistry,
)


def build_source_registry() -> ScraperSourceRegistry:
    """Build registry containing every configured showtime source."""
    registry = ScraperSourceRegistry()
    registry.register("cinemacinema", CinemaCinemaAdapter(CinemaCinemaSource()))
    registry.register("cinemamoderne", CinemaModerneAdapter(CinemaModerneSource()))
    registry.register("cinemapublic", CinemaPublicAdapter(CinemaPublicSource()))
    registry.register("cinestarz", CineStarzAdapter(CineStarzSource()))
    registry.register("cinematheque", CinemathequeAdapter(CinemathequeSource()))
    registry.register("cineplex", CineplexAdapter(CineplexSource()))
    registry.register("outremont", OutremontAdapter(OutremontSource()))
    return registry
