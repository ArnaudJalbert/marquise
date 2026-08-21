"""Snapshot test for the marquise public API surface.

This test enforces that ``marquise.__all__`` contains exactly the intended
public symbols.  If you deliberately expand the public surface, update the
``EXPECTED_PUBLIC_SURFACE`` set and this test will pass again.
"""

from __future__ import annotations

import marquise

EXPECTED_PUBLIC_SURFACE: set[str] = {
    "ApplicationError",
    "CinemaAlreadyExistsError",
    "CinemaController",
    "CinemaIdAlreadyExistsError",
    "CinemaNotFoundError",
    "CinemaSourceAssignmentAlreadyExistsError",
    "CinemaSourceAssignmentNotFoundError",
    "CreateCinemaUseCase",
    "DeleteCinemaUseCase",
    "create_factory",
    "create_factory_session",
    "ListCinemasUseCase",
    "MarquiseFactory",
    "MovieController",
    "MovieNotFoundError",
    "ScreeningAlreadyExistsError",
    "ScreeningController",
    "ScreeningNotFoundError",
    "SourceAlreadyExistsError",
    "SourceController",
    "SourceNotFoundError",
    "TooManyMovieIdsError",
}


def test_public_surface_matches_snapshot() -> None:
    """Verify __all__ matches the expected public surface exactly."""
    assert set(marquise.__all__) == EXPECTED_PUBLIC_SURFACE


def test_all_exported_symbols_are_importable() -> None:
    """Verify every symbol in __all__ can actually be imported from marquise."""
    for name in marquise.__all__:
        assert hasattr(marquise, name), (
            f"marquise.{name} is in __all__ but not importable"
        )
