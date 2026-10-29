"""TMDB response mapping at the movie identity search boundary."""

from unittest.mock import create_autospec

import pytest

from marquise.interface_adapters.repositories.protocols.movie_search_source import (
    MovieSearchError,
    MovieSearchSource,
)
from marquise.interface_adapters.repositories.source_adapters.tmdb import (
    TmdbSearchAdapter,
)


@pytest.mark.asyncio
async def test_tmdb_adapter_labels_candidates_from_injected_source() -> None:
    """The adapter returns an identity that names its provider."""
    source = create_autospec(MovieSearchSource, instance=True)
    source.search.return_value = {
        "total_results": 1,
        "results": [{"id": 42, "title": "Doomsday", "release_date": "2026-12-18"}],
    }

    candidates = await TmdbSearchAdapter(source).search("Docteur Doom", 2026)

    source.search.assert_awaited_once_with("Docteur Doom", 2026)
    assert [(c.provider, c.id, c.title, c.release_year) for c in candidates] == [
        ("tmdb", "42", "Doomsday", 2026)
    ]


@pytest.mark.asyncio
async def test_tmdb_adapter_keeps_zero_and_multiple_hits_distinct() -> None:
    """A no-match stays empty and two hits stay ambiguous."""
    source = create_autospec(MovieSearchSource, instance=True)
    source.search.side_effect = [
        {"total_results": 0, "results": []},
        {
            "total_results": 2,
            "results": [
                {"id": 1, "title": "It", "release_date": "1990-01-01"},
                {"id": 2, "title": "It", "release_date": "2017-01-01"},
            ],
        },
    ]
    adapter = TmdbSearchAdapter(source)

    assert await adapter.search("Unknown", None) == []
    assert [c.id for c in await adapter.search("It", None)] == ["1", "2"]


@pytest.mark.asyncio
async def test_tmdb_adapter_rejects_an_incomplete_page() -> None:
    """A partial page cannot turn two matches into one clear candidate."""
    source = create_autospec(MovieSearchSource, instance=True)
    source.search.return_value = {
        "total_results": 2,
        "results": [{"id": 1, "title": "It"}],
    }

    with pytest.raises(MovieSearchError, match="incomplete"):
        await TmdbSearchAdapter(source).search("It", None)


@pytest.mark.asyncio
async def test_tmdb_adapter_rejects_invalid_response() -> None:
    """Missing result fields never become a fabricated no-match."""
    source = create_autospec(MovieSearchSource, instance=True)
    source.search.return_value = {"results": [{"title": "It"}], "total_results": 1}

    with pytest.raises(MovieSearchError, match="invalid"):
        await TmdbSearchAdapter(source).search("It", None)
