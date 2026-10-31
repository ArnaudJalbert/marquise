"""TMDB facts mapped through a deterministic, fake HTTP transport."""

import json
from copy import deepcopy
from http.client import IncompleteRead
from pathlib import Path
from unittest.mock import create_autospec
from urllib.parse import parse_qs, urlparse

import pytest

from marquise.application.metadata import ProviderIdentity
from marquise.infrastructure.sources.tmdb_metadata import TmdbMetadataHttpSource
from marquise.interface_adapters.repositories.protocols.tmdb_metadata_source import (
    TmdbMetadataSource,
)
from marquise.interface_adapters.repositories.source_adapters.tmdb_metadata import (
    TmdbMetadataAdapter,
)

FIXTURES = Path(__file__).parents[3] / "fixtures" / "tmdb_metadata"
MOVIE = ProviderIdentity("tmdb", "1765072")
PERSON = ProviderIdentity("tmdb", "2001262")


def payloads() -> dict:
    """Return isolated synthetic v3 responses based on issue #350 evidence."""
    return {
        "movie/1765072": json.loads((FIXTURES / "movie.json").read_text()),
        "movie/1765072/translations": json.loads(
            (FIXTURES / "translations.json").read_text()
        ),
        "person/2001262": json.loads((FIXTURES / "person.json").read_text()),
        "movie/1765072/alternative_titles": {
            "titles": [{"title": "Other title", "iso_3166_1": "GB"}]
        },
        "movie/1765072/credits": {
            "crew": [
                {"id": 2001262, "name": "Aakash Kaushik", "job": "Director"},
                {"id": 99, "job": "Producer"},
            ],
            "cast": [{"id": 24, "name": "Performer"}],
        },
        "movie/1765072/images": {
            "posters": [
                {"file_path": "/fr.jpg", "iso_639_1": "fr"},
                {"file_path": "/neutral.jpg", "iso_639_1": None},
            ]
        },
        "movie/1765072/videos:en-US": {
            "results": [
                {
                    "id": "en",
                    "site": "YouTube",
                    "key": "en-key",
                    "type": "Teaser",
                    "official": False,
                    "iso_639_1": "en",
                }
            ]
        },
        "movie/1765072/videos:fr-CA": {
            "results": [
                {
                    "id": "fr",
                    "site": "YouTube",
                    "key": "fr-key",
                    "type": "Trailer",
                    "official": True,
                    "iso_639_1": "fr",
                },
                {
                    "id": "vimeo",
                    "site": "Vimeo",
                    "key": "42",
                    "type": "Clip",
                    "official": False,
                    "iso_639_1": "fr",
                },
            ]
        },
        "movie/1765072/release_dates": {
            "results": [
                {"iso_3166_1": "US", "release_dates": [{"certification": "PG-13"}]},
                {
                    "iso_3166_1": "CA",
                    "release_dates": [{"certification": "PG"}, {"certification": ""}],
                },
            ]
        },
        "search/movie:1": {
            "page": 1,
            "total_pages": 1,
            "total_results": 1,
            "results": [{"id": 1765072, "title": "You Can See Everything"}],
        },
        "search/person:1": {
            "page": 1,
            "total_pages": 1,
            "total_results": 1,
            "results": [{"id": 2001262}],
        },
        "person/2001262/movie_credits": {
            "crew": [
                {"id": 99, "job": "Producer"},
                {"id": 1765072, "job": "Director", "title": "You Can See Everything"},
            ]
        },
    }


def adapter(data: dict, calls: list | None = None) -> TmdbMetadataAdapter:
    """Replay bytes through the real source and adapter, without network I/O."""

    async def fetch(url: str, headers: dict[str, str]) -> bytes:
        parsed = urlparse(url)
        path = parsed.path.removeprefix("/3/")
        params = parse_qs(parsed.query)
        if calls is not None:
            calls.append((path, params))
        key = path
        if path.startswith("search/"):
            key += ":" + params["page"][0]
        if path.endswith("/videos"):
            key += ":" + params["language"][0]
        if path.endswith("/videos") and key not in data:
            return b'{"results": []}'
        response = data[key]
        if isinstance(response, Exception):
            raise response
        return json.dumps(response).encode()

    return TmdbMetadataAdapter(TmdbMetadataHttpSource("fake-secret", fetch=fetch))


@pytest.mark.asyncio
async def test_details_retain_unselected_facts_and_provenance() -> None:
    """Translations, aliases, locales, media and certifications remain facts."""
    result = await adapter(payloads()).movie_details(MOVIE)
    assert result.complete and result.failure is None
    (movie,) = result.items
    assert movie.identity == MOVIE
    assert movie.release_year == 2026 and movie.duration_minutes == 174
    assert [(t.kind, t.title, t.locale) for t in movie.titles] == [
        ("canonical", "You Can See Everything", "en-US"),
        ("original", "You Can See Everything", "en"),
        ("alternative", "Other title", "GB"),
        ("translation", "Vous pouvez tout voir", "fr-CA"),
        ("translation", "You Can See Everything", "en-US"),
    ]
    assert movie.directors[0].identity == PERSON
    assert movie.directors[0].aliases == ("Akash A Kaushik",)
    assert movie.cast[0].name == "Performer"
    assert movie.genres == ("Drama",) and movie.origin_countries == ("CA",)
    assert movie.original_title == "You Can See Everything"
    assert [(v.locale, v.title, v.synopsis, v.poster_url) for v in movie.localized] == [
        ("fr-CA", "Vous pouvez tout voir", "Synopsis canadien", None),
        ("en-US", "You Can See Everything", "English synopsis", None),
        ("fr-FR", None, None, None),
        ("fr", None, None, "https://image.tmdb.org/t/p/original/fr.jpg"),
        ("und", None, None, "https://image.tmdb.org/t/p/original/neutral.jpg"),
    ]
    assert [(m.language, m.kind, m.official) for m in movie.media] == [
        ("en", "teaser", False),
        ("fr", "trailer", True),
        ("fr", "other", False),
    ]
    assert movie.media[1].url == "https://www.youtube.com/watch?v=fr-key"
    assert [(c.country, c.rating) for c in movie.certifications] == [
        ("US", "PG-13"),
        ("CA", "PG"),
    ]


@pytest.mark.asyncio
async def test_people_and_directed_credits_do_not_choose_a_person_or_movie() -> None:
    """Ambiguous people and directed-film credit order survive mapping."""
    data = payloads()
    data["search/person:1"]["results"].append({"id": 17})
    data["search/person:1"]["total_results"] = 2
    data["person/17"] = {"id": 17, "name": "Another person", "also_known_as": []}
    repository = adapter(data)
    people = await repository.search_people("Akash A Kaushik")
    assert people.complete and [p.identity for p in people.items] == [
        PERSON,
        ProviderIdentity("tmdb", "17"),
    ]
    assert people.items[0].aliases == ("Akash A Kaushik",)
    films = await repository.directed_movies(PERSON)
    assert films.complete and [m.identity for m in films.items] == [MOVIE]


@pytest.mark.asyncio
async def test_search_paginates_and_retains_provider_order_and_filters() -> None:
    """Later-page candidates are hydrated without sorting or selection."""
    data = payloads()
    data["search/movie:1"].update(total_pages=2, total_results=2)
    data["search/movie:2"] = {
        "page": 2,
        "total_pages": 2,
        "total_results": 2,
        "results": [{"id": 680770, "title": "Le Monde de Wishy"}],
    }
    for key, value in list(data.items()):
        if key.startswith("movie/1765072"):
            copied = deepcopy(value)
            if "id" in copied:
                copied["id"] = 680770
            data[key.replace("1765072", "680770")] = copied
    data["movie/680770/translations"]["translations"][0]["data"]["title"] = (
        "Le Monde de Wishy"
    )
    calls: list = []
    result = await adapter(data, calls).search_movies("Wishy", 2026)
    assert result.complete and [m.identity.id for m in result.items] == [
        "1765072",
        "680770",
    ]
    assert result.items[1].titles[0].title == "Le Monde de Wishy"
    assert not any(path.startswith("movie/") for path, _ in calls)
    search_calls = [params for path, params in calls if path == "search/movie"]
    assert [p["page"] for p in search_calls] == [["1"], ["2"]]
    assert all(p["primary_release_year"] == ["2026"] for p in search_calls)


@pytest.mark.asyncio
async def test_failed_later_page_preserves_partial_facts() -> None:
    """A failed second page never masquerades as exhaustive search absence."""
    data = payloads()
    data["search/movie:1"].update(total_pages=2, total_results=2)
    data["search/movie:2"] = OSError("fake-secret")
    result = await adapter(data).search_movies("Anything")
    assert not result.complete and result.failure.kind == "unavailable"
    assert result.items[0].identity == MOVIE
    assert "fake-secret" not in repr(result)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "endpoint,field,value",
    [
        ("movie/1765072", "runtime", "174"),
        ("movie/1765072", "id", True),
        ("movie/1765072", "release_date", "bad-date"),
        ("movie/1765072/translations", "translations", {}),
        ("movie/1765072/credits", "crew", [None]),
        ("person/2001262", "also_known_as", [17]),
        ("person/2001262", "id", 44),
        ("movie/1765072/videos:en-US", "results", [{"id": "x"}]),
    ],
)
async def test_malformed_facts_are_typed_incomplete(
    endpoint: str, field: str, value: str | bool | int | dict | list
) -> None:
    """Malformed JSON facts cannot become valid complete metadata."""
    data = payloads()
    data[endpoint][field] = value
    result = await adapter(data).movie_details(MOVIE)
    assert not result.complete and result.failure.kind == "invalid_data"


@pytest.mark.asyncio
async def test_failed_details_keep_already_mapped_facts() -> None:
    """A late transport failure preserves text but cannot claim enrichment success."""
    data = payloads()
    data["movie/1765072/credits"] = OSError("secret")
    result = await adapter(data).movie_details(MOVIE)
    assert not result.complete and result.items[0].localized[0].locale == "fr-CA"
    assert result.failure.kind == "unavailable"


@pytest.mark.asyncio
async def test_adapter_uses_autospecced_gateway_and_rejects_foreign_identity() -> None:
    """Foreign identities cannot trigger TMDB I/O or leak into TMDB facts."""
    source = create_autospec(TmdbMetadataSource, instance=True)
    repository = TmdbMetadataAdapter(source)
    result = await repository.movie_details(ProviderIdentity("other", "1765072"))
    assert not result.complete and result.failure.kind == "invalid_data"
    source.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_optional_values_do_not_invent_fallback_text() -> None:
    """Absent translation text and zero runtime remain unselected raw evidence."""
    data = payloads()
    data["movie/1765072"].update(runtime=0, release_date="", original_title=None)
    data["movie/1765072/translations"]["translations"][0]["data"] = {
        "title": "",
        "overview": None,
    }
    calls: list = []
    result = await adapter(data, calls).movie_details(MOVIE)
    assert result.complete
    (movie,) = result.items
    assert movie.duration_minutes == 0 and movie.release_year is None
    assert movie.original_title is None
    assert movie.localized[0].title is None and movie.localized[0].synopsis is None
    assert any(m.language == "fr" for m in movie.media)
    assert any(
        path.endswith("/videos") and params["language"] == ["fr-CA"]
        for path, params in calls
    )


@pytest.mark.asyncio
async def test_people_pagination_and_partial_alias_failure() -> None:
    """All people pages are inspected, and an alias failure is never absence."""
    data = payloads()
    data["search/person:1"].update(total_pages=2, total_results=2)
    data["search/person:2"] = {
        "page": 2,
        "total_pages": 2,
        "total_results": 2,
        "results": [{"id": 17}],
    }
    data["person/17"] = OSError("private")
    result = await adapter(data).search_people("Kaushik")
    assert not result.complete and result.failure.kind == "unavailable"
    assert [p.identity for p in result.items] == [PERSON]


@pytest.mark.asyncio
async def test_media_duplicates_across_locale_requests_keep_first_provider_order() -> (
    None
):
    """The same video returned for several locales is one fact, without ranking."""
    data = payloads()
    data["movie/1765072/videos:fr-CA"]["results"].insert(
        0, deepcopy(data["movie/1765072/videos:en-US"]["results"][0])
    )
    result = await adapter(data).movie_details(MOVIE)
    assert result.complete
    assert [m.kind for m in result.items[0].media] == ["teaser", "trailer", "other"]


@pytest.mark.asyncio
async def test_truncated_http_detail_returns_typed_partial_batch() -> None:
    """A truncated body remains an incomplete result rather than a raw exception."""
    data = payloads()
    data["movie/1765072/credits"] = IncompleteRead(b"fake-secret", 100)
    result = await adapter(data).movie_details(MOVIE)
    assert not result.complete and result.failure.kind == "unavailable"
    assert result.failure.retryable and result.items[0].identity == MOVIE
    assert "fake-secret" not in repr(result)
