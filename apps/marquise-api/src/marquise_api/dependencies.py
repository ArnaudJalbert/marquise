"""Factory-backed FastAPI dependencies."""

from __future__ import annotations

from fastapi import Request

from marquise import (
    BrowseScreeningMoviesQuery,
    CountScreeningDaysQuery,
    GetCinemaMoviesUseCase,
    GetCinemaScreeningsQuery,
    GetCinemaUseCase,
    GetMovieScreeningsQuery,
    GetMovieUseCase,
    GetScreeningQuery,
    ListCinemasUseCase,
    ListMoviesUseCase,
    MarquiseFactory,
    SearchScreeningsQuery,
)


def get_factory(request: Request) -> MarquiseFactory:
    """Return initialized factory stored on application state."""
    return request.app.state.factory


def get_list_cinemas_use_case(request: Request) -> ListCinemasUseCase:
    """Return configured cinema-listing use case."""
    return request.app.state.factory.cinemas.list_cinemas_use_case


def get_cinema_use_case(request: Request) -> GetCinemaUseCase:
    """Return configured cinema lookup use case."""
    return request.app.state.factory.cinemas.get_cinema_use_case


def get_cinema_screenings_query(request: Request) -> GetCinemaScreeningsQuery:
    """Return configured cinema-screenings query."""
    return request.app.state.factory.cinemas.get_cinema_screenings_query


def get_cinema_movies_use_case(request: Request) -> GetCinemaMoviesUseCase:
    """Return configured cinema-movies use case."""
    return request.app.state.factory.cinemas.get_cinema_movies_use_case


def get_list_movies_use_case(request: Request) -> ListMoviesUseCase:
    """Return configured movie-listing use case."""
    return request.app.state.factory.movies.list_movies_use_case


def get_movie_use_case(request: Request) -> GetMovieUseCase:
    """Return configured movie lookup use case."""
    return request.app.state.factory.movies.get_movie_use_case


def get_movie_screenings_query(request: Request) -> GetMovieScreeningsQuery:
    """Return configured movie-screenings query."""
    return request.app.state.factory.movies.get_movie_screenings_query


def get_search_screenings_query(request: Request) -> SearchScreeningsQuery:
    """Return configured screening-search query."""
    return request.app.state.factory.screenings.search_screenings_query


def get_screening_query(request: Request) -> GetScreeningQuery:
    """Return configured screening lookup query."""
    return request.app.state.factory.screenings.get_screening_query


def get_browse_screening_movies_query(request: Request) -> BrowseScreeningMoviesQuery:
    """Return the configured movie-first screening query."""
    return request.app.state.factory.screenings.browse_screening_movies_query


def get_count_screening_days_query(request: Request) -> CountScreeningDaysQuery:
    """Return the configured daily screening-count query."""
    return request.app.state.factory.screenings.count_screening_days_query
