"""Tests for EnsureMoviesExistCommand."""

from __future__ import annotations

from unittest.mock import create_autospec

import pytest

from marquise.application.repositories import (
    MovieRepository,
    SourceRegistryQuery,
)
from marquise.application.repositories.source_registry_query import (
    MovieEnrichmentData,
)
from marquise.application.use_cases.ensure_movies_exist import EnsureMoviesExistCommand
from marquise.domain.entities import Movie
from marquise.domain.value_objects import MovieId


def _make_input_row(
    movie_title: str = "Test Movie",
    identifier: str | None = None,
) -> EnsureMoviesExistCommand.InputRow:
    return EnsureMoviesExistCommand.InputRow(
        movie_title=movie_title,
        identifier=identifier,
    )


def _make_command(
    movie_repo: MovieRepository,
    registry: SourceRegistryQuery,
) -> EnsureMoviesExistCommand:
    return EnsureMoviesExistCommand(
        movie_repository=movie_repo,
        source_registry=registry,
    )


async def _run(
    command: EnsureMoviesExistCommand,
    rows: tuple[EnsureMoviesExistCommand.InputRow, ...],
    source_name: str = "cinemacinema",
) -> dict[str, str]:
    result = await command.execute(
        EnsureMoviesExistCommand.InputData(rows=rows, source_name=source_name)
    )
    return result.movie_lookup


@pytest.mark.asyncio
async def test_creates_missing_movies() -> None:
    """Test that a movie is created for every missing title."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    rows = (
        _make_input_row("Movie A"),
        _make_input_row("Movie B"),
    )
    mock_movie_repo.find_by_titles.return_value = {
        "Movie A": None,
        "Movie B": None,
    }
    movie_a = Movie(id=MovieId(value="mov-a"), title="Movie A")
    movie_b = Movie(id=MovieId(value="mov-b"), title="Movie B")
    mock_movie_repo.save.side_effect = [movie_a, movie_b]

    lookup = await _run(_make_command(mock_movie_repo, mock_registry), rows)

    assert lookup["Movie A"] == "mov-a"
    assert lookup["Movie B"] == "mov-b"
    assert mock_movie_repo.save.await_count == 2


@pytest.mark.asyncio
async def test_reuses_existing_movie() -> None:
    """Test that an existing movie is reused (not created again)."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    movie_a = Movie(id=MovieId(value="mov-a"), title="Movie A")
    mock_movie_repo.find_by_titles.return_value = {"Movie A": movie_a}

    lookup = await _run(
        _make_command(mock_movie_repo, mock_registry),
        (_make_input_row("Movie A"),),
    )

    assert lookup["Movie A"] == "mov-a"
    mock_movie_repo.find_by_titles.assert_awaited()
    mock_movie_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_dedupes_titles_differing_by_whitespace() -> None:
    """Test that titles differing only by whitespace share a single movie."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    rows = (
        _make_input_row("Beau Is Afraid"),
        _make_input_row("  Beau  Is  Afraid "),
    )
    mock_movie_repo.find_by_titles.return_value = {"Beau Is Afraid": None}
    saved_movie = Movie(id=MovieId(value="mov-a"), title="Beau Is Afraid")
    mock_movie_repo.save.return_value = saved_movie

    lookup = await _run(_make_command(mock_movie_repo, mock_registry), rows)

    # Both rows normalize to the same title, so only one movie gets created.
    mock_movie_repo.save.assert_awaited_once()
    created_movie = mock_movie_repo.save.call_args[0][0]
    assert created_movie.title == "Beau Is Afraid"
    assert lookup["Beau Is Afraid"] == "mov-a"


@pytest.mark.asyncio
async def test_reuses_movie_found_with_different_case() -> None:
    """Test that a case-insensitive match still enriches and re-links correctly.

    Regression test: re-keying the movie lookup by the *saved entity's* title
    (rather than the query title) after a case-insensitive find_by_title match
    would silently orphan the row's own lookup key, losing the enrichment.
    """
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    # Stored under a different case than today's scrape, and missing
    # optional fields so it qualifies for enrichment.
    existing_movie = Movie(id=MovieId(value="mov-batman"), title="the batman")
    mock_movie_repo.find_by_titles.return_value = {"The Batman": existing_movie}

    enrichment = MovieEnrichmentData(description="The Dark Knight returns")
    mock_registry.fetch_movie_detail.return_value = enrichment

    enriched_movie = Movie(
        id=MovieId(value="mov-batman"),
        title="the batman",
        description="The Dark Knight returns",
    )
    mock_movie_repo.save.return_value = enriched_movie

    lookup = await _run(
        _make_command(mock_movie_repo, mock_registry),
        (_make_input_row("The Batman", identifier="the-batman-slug"),),
    )

    # The row's normalized key must map to the enriched movie ID.
    assert lookup["The Batman"] == "mov-batman"


@pytest.mark.asyncio
async def test_enriches_new_movie_with_all_fields() -> None:
    """Test that enrichment populates all optional fields on a new movie."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    mock_movie_repo.find_by_titles.return_value = {"Rich Movie": None}

    enrichment = MovieEnrichmentData(
        description="A rich movie",
        directors=("Director",),
        cast=("Actor A", "Actor B"),
        duration_minutes=100,
        release_year=2026,
        poster_url="https://example.com/poster.jpg",
        trailer_url="https://example.com/trailer",
        genres=("Drama", "Thriller"),
        original_title="Original Title",
        rating="PG-13",
        origin_countries=("US", "UK"),
    )
    mock_registry.fetch_movie_detail.return_value = enrichment

    saved_movie = Movie(
        id=MovieId(value="mov-rich"),
        title="Rich Movie",
        description="A rich movie",
        directors=("Director",),
        cast=("Actor A", "Actor B"),
        duration_minutes=100,
        release_year=2026,
        poster_url="https://example.com/poster.jpg",
        trailer_url="https://example.com/trailer",
        genres=("Drama", "Thriller"),
        original_title="Original Title",
        rating="PG-13",
        origin_countries=("US", "UK"),
    )
    mock_movie_repo.save.return_value = saved_movie

    await _run(
        _make_command(mock_movie_repo, mock_registry),
        (_make_input_row("Rich Movie", identifier="rich-slug"),),
    )

    saved = mock_movie_repo.save.call_args[0][0]
    assert saved.description == "A rich movie"
    assert saved.directors == ("Director",)
    assert saved.cast == ("Actor A", "Actor B")
    assert saved.duration_minutes == 100
    assert saved.release_year == 2026
    assert saved.poster_url == "https://example.com/poster.jpg"
    assert saved.trailer_url == "https://example.com/trailer"
    assert saved.genres == ("Drama", "Thriller")
    assert saved.original_title == "Original Title"
    assert saved.rating == "PG-13"
    assert saved.origin_countries == ("US", "UK")


@pytest.mark.asyncio
async def test_enriches_new_movie_with_identifier() -> None:
    """Test that a new movie with an identifier is enriched from the source."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    mock_movie_repo.find_by_titles.return_value = {"New Movie": None}

    enrichment = MovieEnrichmentData(
        description="A great new movie",
        duration_minutes=120,
        directors=("Director A",),
        release_year=2026,
    )
    mock_registry.fetch_movie_detail.return_value = enrichment

    saved_movie = Movie(
        id=MovieId(value="mov-new"),
        title="New Movie",
        description="A great new movie",
        duration_minutes=120,
        directors=("Director A",),
        release_year=2026,
    )
    mock_movie_repo.save.return_value = saved_movie

    await _run(
        _make_command(mock_movie_repo, mock_registry),
        (_make_input_row("New Movie", identifier="new-movie-slug"),),
    )

    mock_registry.fetch_movie_detail.assert_awaited_once_with(
        "cinemacinema", "new-movie-slug"
    )
    mock_movie_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_enriches_existing_movie_with_null_fields() -> None:
    """Test that an existing movie with null fields gets enriched."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    existing_movie = Movie(
        id=MovieId(value="mov-existing"),
        title="Existing Movie",
        directors=("Old Director",),
        description=None,
        duration_minutes=None,
    )
    mock_movie_repo.find_by_titles.return_value = {"Existing Movie": existing_movie}

    enrichment = MovieEnrichmentData(
        description="An existing movie with new details",
        duration_minutes=130,
    )
    mock_registry.fetch_movie_detail.return_value = enrichment
    mock_movie_repo.save.return_value = Movie(
        id=MovieId(value="mov-existing"),
        title="Existing Movie",
        directors=("Old Director",),
        description="An existing movie with new details",
        duration_minutes=130,
    )

    await _run(
        _make_command(mock_movie_repo, mock_registry),
        (_make_input_row("Existing Movie", identifier="existing-slug"),),
    )

    mock_registry.fetch_movie_detail.assert_awaited_once_with(
        "cinemacinema", "existing-slug"
    )
    mock_movie_repo.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_does_not_refetch_already_enriched_movie() -> None:
    """Test that an already-enriched movie is not fetched again."""
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    enriched_movie = Movie(
        id=MovieId(value="mov-enriched"),
        title="Full Movie",
        directors=("Director",),
        cast=("Actor",),
        duration_minutes=120,
        description="Already known",
        release_year=2025,
        poster_url="https://example.com/poster.jpg",
        trailer_url="https://example.com/trailer",
        genres=("Drama",),
        original_title="Full Movie",
        rating="PG",
        origin_countries=("US",),
    )
    mock_movie_repo.find_by_titles.return_value = {"Full Movie": enriched_movie}

    await _run(
        _make_command(mock_movie_repo, mock_registry),
        (_make_input_row("Full Movie", identifier="full-slug"),),
    )

    mock_registry.fetch_movie_detail.assert_not_awaited()
    mock_movie_repo.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_handles_mixed_identifiers_for_enrichment() -> None:
    """Test enrichment alignment when some movies have identifiers and some don't.

    This regression test validates the fix for the enrichment misalignment bug
    where ``enrich_identifiers`` was shorter than ``enrich_titles``, causing
    enrichment results to be applied to the wrong movie.
    """
    mock_movie_repo = create_autospec(MovieRepository, instance=True)
    mock_registry = create_autospec(SourceRegistryQuery, instance=True)

    rows = (
        _make_input_row("Movie With ID", identifier="has-id"),
        _make_input_row("Movie Without ID", identifier=None),
    )
    mock_movie_repo.find_by_titles.return_value = {
        "Movie With ID": None,
        "Movie Without ID": None,
    }

    enrichment = MovieEnrichmentData(
        description="Only movie with ID gets enriched",
        duration_minutes=100,
    )
    mock_registry.fetch_movie_detail.return_value = enrichment

    movie_with_id = Movie(
        id=MovieId(value="mov-id"),
        title="Movie With ID",
        description="Only movie with ID gets enriched",
        duration_minutes=100,
    )
    movie_without_id = Movie(id=MovieId(value="mov-no-id"), title="Movie Without ID")

    def save_side_effect(movie: Movie) -> Movie:
        if movie.title == "Movie With ID":
            return movie_with_id
        return movie_without_id

    mock_movie_repo.save.side_effect = save_side_effect

    await _run(_make_command(mock_movie_repo, mock_registry), rows)

    mock_registry.fetch_movie_detail.assert_awaited_once_with("cinemacinema", "has-id")
    assert mock_movie_repo.save.await_count == 2

    saved_movie_with_id = mock_movie_repo.save.call_args_list[0][0][0]
    assert saved_movie_with_id.title == "Movie With ID"
    assert saved_movie_with_id.description == "Only movie with ID gets enriched"
    assert saved_movie_with_id.duration_minutes == 100
