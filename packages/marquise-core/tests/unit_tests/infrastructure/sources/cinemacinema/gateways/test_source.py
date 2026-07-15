"""Tests for the Cinéma Cinéma showtime source gateway."""

from __future__ import annotations

from marquise.infrastructure.sources.cinemacinema.gateways.source import (
    _extract_film_detail,
)


def _film(**overrides: object) -> dict:
    """Build a minimal ``cmFilmCurrent``-shaped dict, mirroring the real API."""
    film = {
        "realisateur": "",
        "acteurs": "",
        "genre1": "",
        "genre2": "",
        "genre3": "",
        "origine1": "",
        "origine2": "",
        "origine3": "",
        "synopsis": "",
        "duree": None,
        "annee": None,
        "poster_url": None,
        "bande_annonce_url": None,
        "classment": None,
        "original_title": None,
    }
    film.update(overrides)
    return film


def test_extract_film_detail_rejects_zero_release_year() -> None:
    """A film with ``annee: 0`` (unknown release date) yields no release year."""
    result = _extract_film_detail(_film(annee=0))

    assert result["release_year"] is None


def test_extract_film_detail_rejects_negative_release_year() -> None:
    """A negative ``annee`` value yields no release year."""
    result = _extract_film_detail(_film(annee=-5))

    assert result["release_year"] is None


def test_extract_film_detail_handles_missing_release_year() -> None:
    """A film with no ``annee`` field yields no release year."""
    result = _extract_film_detail(_film())

    assert result["release_year"] is None


def test_extract_film_detail_parses_valid_release_year() -> None:
    """A well-formed positive ``annee`` int is parsed as the release year."""
    result = _extract_film_detail(_film(annee=2023))

    assert result["release_year"] == 2023


def test_extract_film_detail_parses_numeric_string_release_year() -> None:
    """A numeric string ``annee`` value is parsed as the release year."""
    result = _extract_film_detail(_film(annee="2023"))

    assert result["release_year"] == 2023


def test_extract_film_detail_rejects_non_numeric_release_year() -> None:
    """A non-numeric string ``annee`` value yields no release year."""
    result = _extract_film_detail(_film(annee="unknown"))

    assert result["release_year"] is None
