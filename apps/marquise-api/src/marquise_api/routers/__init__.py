"""API routers."""

from marquise_api.routers.cinemas import router as cinemas_router
from marquise_api.routers.movies import router as movies_router
from marquise_api.routers.screening_movies import router as screening_movies_router
from marquise_api.routers.screenings import router as screenings_router

__all__ = [
    "cinemas_router",
    "screening_movies_router",
    "movies_router",
    "screenings_router",
]
