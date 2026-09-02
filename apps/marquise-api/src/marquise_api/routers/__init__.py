"""API routers."""

from marquise_api.routers.auth import router as auth_router
from marquise_api.routers.cinemas import router as cinemas_router
from marquise_api.routers.movies import router as movies_router
from marquise_api.routers.screenings import router as screenings_router

__all__ = [
    "auth_router",
    "cinemas_router",
    "movies_router",
    "screenings_router",
]
