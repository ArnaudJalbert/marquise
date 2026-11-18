"""Wired use cases grouped by area, one immutable container per area."""

from marquise.infrastructure.di.use_case_areas.cinemas import (
    CinemaUseCases,
    build_cinema_use_cases,
)
from marquise.infrastructure.di.use_case_areas.movies import (
    MovieUseCases,
    build_movie_use_cases,
)
from marquise.infrastructure.di.use_case_areas.screenings import (
    ScreeningUseCases,
    build_screening_use_cases,
)
from marquise.infrastructure.di.use_case_areas.sources import (
    SourceUseCases,
    build_source_use_cases,
)

__all__ = [
    "CinemaUseCases",
    "MovieUseCases",
    "ScreeningUseCases",
    "SourceUseCases",
    "build_cinema_use_cases",
    "build_movie_use_cases",
    "build_screening_use_cases",
    "build_source_use_cases",
]
