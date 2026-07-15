"""API routers."""

from marquise.infrastructure.api.routers.cinemas import router as cinemas_router
from marquise.infrastructure.api.routers.movies import router as movies_router
from marquise.infrastructure.api.routers.screenings import router as screenings_router

__all__ = ["cinemas_router", "movies_router", "screenings_router"]
