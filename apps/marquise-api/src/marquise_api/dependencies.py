"""Factory-backed FastAPI dependencies."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

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
    VerifyAccessTokenQuery,
    WriteScreeningUseCase,
)


def get_factory(request: Request) -> MarquiseFactory:
    """Return initialized factory stored on application state."""
    return request.app.state.factory


def get_verify_access_token_query(request: Request) -> VerifyAccessTokenQuery:
    """Return the configured access-token query or report unavailable auth."""
    try:
        query = get_factory(request).verify_access_token_query
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        ) from exc
    if query is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured",
        )
    return query


def get_list_cinemas_use_case(request: Request) -> ListCinemasUseCase:
    """Return configured cinema-listing use case."""
    return request.app.state.factory.list_cinemas_use_case


def get_cinema_use_case(request: Request) -> GetCinemaUseCase:
    """Return configured cinema lookup use case."""
    return request.app.state.factory.get_cinema_use_case


def get_cinema_screenings_query(request: Request) -> GetCinemaScreeningsQuery:
    """Return configured cinema-screenings query."""
    return request.app.state.factory.get_cinema_screenings_query


def get_cinema_movies_use_case(request: Request) -> GetCinemaMoviesUseCase:
    """Return configured cinema-movies use case."""
    return request.app.state.factory.get_cinema_movies_use_case


def get_list_movies_use_case(request: Request) -> ListMoviesUseCase:
    """Return configured movie-listing use case."""
    return request.app.state.factory.list_movies_use_case


def get_movie_use_case(request: Request) -> GetMovieUseCase:
    """Return configured movie lookup use case."""
    return request.app.state.factory.get_movie_use_case


def get_movie_screenings_query(request: Request) -> GetMovieScreeningsQuery:
    """Return configured movie-screenings query."""
    return request.app.state.factory.get_movie_screenings_query


def get_search_screenings_query(request: Request) -> SearchScreeningsQuery:
    """Return configured screening-search query."""
    return request.app.state.factory.search_screenings_query


def get_write_screening_use_case(request: Request) -> WriteScreeningUseCase:
    """Return configured audited, retry-safe screening write orchestration."""
    return request.app.state.factory.write_screening_use_case


def get_screening_query(request: Request) -> GetScreeningQuery:
    """Return configured screening lookup query."""
    return request.app.state.factory.get_screening_query


def get_browse_screening_movies_query(request: Request) -> BrowseScreeningMoviesQuery:
    """Return the configured movie-first screening query."""
    return request.app.state.factory.browse_screening_movies_query


def get_count_screening_days_query(request: Request) -> CountScreeningDaysQuery:
    """Return the configured daily screening-count query."""
    return request.app.state.factory.count_screening_days_query
