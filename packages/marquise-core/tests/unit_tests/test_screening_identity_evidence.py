"""Screening source identity evidence and title preservation."""

import json
from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import MovieRepository
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId
from marquise.infrastructure.sources.cinemamoderne.gateways.source import (
    _extract_cinemamoderne_film_detail,
)
from marquise.infrastructure.sources.cineplex.gateways.source import (
    _extract_movie_detail,
)
from support.movie_import import build_match, build_matcher, build_movie_import


def test_festival_label_produces_identity_title() -> None:
    """A festival label is removed only from the lookup title."""
    detail = _extract_cinemamoderne_film_detail("<h1>CINEMANIA: Julián</h1>")
    assert detail["identity_title"] == "Julián"
    assert "identity_title" not in _extract_cinemamoderne_film_detail(
        "<h1>A Film: Part Two</h1>"
    )


def test_cineplex_extracts_attributed_identity() -> None:
    """An attributed filmmaker and title in the source synopsis are retained."""
    movie = {
        "synopsis": (
            "From acclaimed filmmaker David Ayer, "
            "Heart of the Beast is an intense adventure."
        ),
        "director": "",
        "releaseDate": "2026-01-01",
    }
    payload = json.dumps({"props": {"pageProps": {"movieDetails": movie}}})
    detail = _extract_movie_detail(
        f'<script id="__NEXT_DATA__" type="application/json">{payload}</script>'
    )
    assert detail is not None
    assert detail["identity_title"] == "Heart of the Beast"
    assert detail["directors"] == ["David Ayer"]


@pytest.mark.asyncio
async def test_identity_lookup_preserves_screening_label() -> None:
    """Lookup uses the film title and returns the original screening label."""
    repo = create_autospec(MovieRepository, instance=True)
    matcher = build_matcher(build_match("123"))
    repo.find_by_tmdb_id.return_value = Movie(
        id=MovieId(value="existing"), title="Julián", tmdb_id="123"
    )
    command = build_movie_import(repo, matcher)
    result = await command.execute(
        command.InputData(
            movies=(
                command.build_movie_input(
                    title="CINEMANIA: Julián",
                    identity_title="Julián",
                    release_year=2025,
                ),
            )
        )
    )
    request = matcher.execute.await_args.args[0].movies[0]
    assert (request.identity_title, request.release_year) == ("Julián", 2025)
    assert result.movies == (
        command.MovieData(title="CINEMANIA: Julián", id="existing"),
    )
