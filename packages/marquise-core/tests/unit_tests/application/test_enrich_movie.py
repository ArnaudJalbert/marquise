"""Deterministic enrichment policy tests with atomic in-memory persistence."""

from collections.abc import Callable
from dataclasses import fields, replace
from datetime import UTC, datetime
from unittest.mock import Mock, create_autospec

import pytest

from marquise.application.exceptions import (
    MetadataRateLimitedError,
    MetadataUnavailableError,
)
from marquise.application.metadata import (
    LocalizedMovieMetadata,
    MetadataBatch,
    MetadataMovie,
    MetadataRepository,
    MovieCertification,
    MovieMedia,
    PersonFact,
    ProviderIdentity,
    TitleFact,
)
from marquise.application.movie_workflows import (
    EnrichMovieInputData,
    EnrichMovieOutputData,
    MovieMetadataRepository,
    MovieMetadataSnapshot,
    MovieMetadataValues,
    MovieWorkflowConflictError,
    RefreshMoviesInputData,
)
from marquise.application.use_cases.enrich_movies import _enrich, _select_values
from marquise.application.use_cases.refresh_movies import RefreshMoviesUseCase

NOW = datetime(2026, 10, 30, tzinfo=UTC)
IDENTITY = ProviderIdentity("tmdb", "123")
REQUEST = EnrichMovieInputData("stable-movie", IDENTITY)
SOURCE = MovieMetadataValues(
    title="Source",
    original_title="Original source",
    description="Source synopsis",
    release_year=1976,
    duration_minutes=98,
    directors=("Source director",),
    cast=("Source actor",),
    genres=("Source genre",),
    origin_countries=("Source country",),
    poster_url="https://source/poster",
    trailer_url="https://source/trailer",
    rating="Source rating",
)


@pytest.fixture
def movies() -> Mock:
    """Autospecced port whose fake writes preserve unspecified fields atomically."""
    repository = create_autospec(MovieMetadataRepository, instance=True)
    state = {
        "stable-movie": MovieMetadataSnapshot(
            "stable-movie", "revision-1", SOURCE, screening_ids=("stable-screening",)
        )
    }

    async def get(movie_id: str) -> MovieMetadataSnapshot | None:
        return state.get(movie_id)

    async def update(
        expected: MovieMetadataSnapshot,
        values: MovieMetadataValues,
        tmdb_id: str,
        enriched_at: datetime,
    ) -> MovieMetadataSnapshot:
        assert state[expected.movie_id] == expected
        selected = {
            field.name: getattr(values, field.name)
            for field in fields(values)
            if getattr(values, field.name) is not None
        }
        updated = replace(
            expected,
            values=replace(expected.values, **selected),
            tmdb_id=tmdb_id,
            metadata_enriched_at=enriched_at,
            revision=expected.revision + "-updated",
        )
        state[expected.movie_id] = updated
        return updated

    async def list_movies() -> tuple[MovieMetadataSnapshot, ...]:
        return tuple(item for item in state.values() if item.tmdb_id)

    repository.get.side_effect = get
    repository.update_metadata.side_effect = update
    repository.list_tmdb_movies.side_effect = list_movies
    return repository


@pytest.fixture
def metadata() -> Mock:
    """Return structured facts, without selecting a locale or field winner."""
    repository = create_autospec(MetadataRepository, instance=True)
    repository.movie_details.return_value = MetadataBatch(
        (MetadataMovie(IDENTITY, (), tmdb_vote_count=0),)
    )
    return repository


class EnrichPolicy:
    """Drive the enrichment policy shared by batch enrichment and refresh."""

    def __init__(self, movies: Mock, metadata: Mock, clock: Callable) -> None:
        self._dependencies = (movies, metadata, clock)

    async def execute(self, request: EnrichMovieInputData) -> EnrichMovieOutputData:
        """Apply the policy to one movie."""
        return await _enrich(request, *self._dependencies)


def use_case(movies: Mock, metadata: Mock) -> EnrichPolicy:
    """Build the policy with a fixed successful-write timestamp."""
    return EnrichPolicy(movies, metadata, lambda: NOW)


@pytest.mark.asyncio
async def test_selects_all_fields_and_preserves_stable_ids(
    movies: Mock, metadata: Mock
) -> None:
    """English values win per field and only the intended ID is patched."""
    person = PersonFact(ProviderIdentity("tmdb", "person"), " Director ")
    metadata.movie_details.return_value = MetadataBatch(
        (
            MetadataMovie(
                IDENTITY,
                (),
                original_title=" Original ",
                release_year=2025,
                duration_minutes=101,
                directors=(person,),
                cast=(replace(person, name="Actor"),),
                genres=(" Drama ",),
                origin_countries=("Canada",),
                localized=(
                    LocalizedMovieMetadata(
                        "en-US", "English", "English synopsis", "https://en/poster"
                    ),
                    LocalizedMovieMetadata("fr-FR", "France", "France synopsis"),
                    LocalizedMovieMetadata(
                        "fr-CA", " Québec ", " ", "https://fr/poster"
                    ),
                ),
                media=(
                    MovieMedia("https://en/trailer", "en", "trailer", True),
                    MovieMedia("https://fr/teaser", "fr", "teaser", True),
                    MovieMedia("https://fr/unofficial", "fr", "trailer", False),
                    MovieMedia("https://fr/trailer", "fr", "trailer", True),
                ),
                certifications=(
                    MovieCertification("US", "R"),
                    MovieCertification("CA", "14A"),
                ),
                tmdb_rating=8.1,
                tmdb_vote_count=1234,
            ),
        )
    )
    result = await use_case(movies, metadata).execute(REQUEST)
    assert result.status == "enriched"
    snapshot = await movies.get(REQUEST.movie_id)
    assert snapshot.movie_id == REQUEST.movie_id
    assert snapshot.screening_ids == ("stable-screening",)
    assert snapshot.tmdb_id == "123"
    assert snapshot.metadata_enriched_at == NOW
    assert snapshot.values == MovieMetadataValues(
        title="English",
        original_title="Original",
        description="English synopsis",
        release_year=2025,
        duration_minutes=101,
        directors=("Director",),
        cast=("Actor",),
        genres=("Drama",),
        origin_countries=("Canada",),
        poster_url="https://en/poster",
        trailer_url="https://en/trailer",
        rating="14A",
        tmdb_rating=8.1,
        tmdb_vote_count=1234,
    )
    metadata.movie_details.assert_awaited_once_with(IDENTITY)
    movies.update_metadata.assert_awaited_once()
    expected, values, tmdb_id, timestamp = movies.update_metadata.call_args.args
    assert expected.revision == "revision-1"
    assert expected.values == SOURCE
    assert values == snapshot.values
    assert (tmdb_id, timestamp) == ("123", NOW)
    movies.find_by_tmdb_id.assert_not_awaited()
    movies.merge.assert_not_awaited()


@pytest.mark.asyncio
async def test_french_fallback_and_provider_order(movies: Mock, metadata: Mock) -> None:
    """French fills absent English media, never the title; ties keep provider order."""
    metadata.movie_details.return_value = MetadataBatch(
        (
            MetadataMovie(
                IDENTITY,
                (),
                localized=(
                    LocalizedMovieMetadata(
                        "fr-FR",
                        "Wrong fallback",
                        "Wrong synopsis",
                        "https://wrong/poster",
                    ),
                    LocalizedMovieMetadata(
                        "fr-CA", "Québec", "Synopsis", "https://fr/poster"
                    ),
                ),
                media=(
                    MovieMedia("broken", "en", "trailer", True),
                    MovieMedia("https://fr/first", "fr", "trailer", True),
                    MovieMedia("https://fr/second", "fr", "trailer", True),
                ),
                certifications=(
                    MovieCertification("CA", " "),
                    MovieCertification("CA", "G"),
                    MovieCertification("CA", "PG"),
                ),
            ),
        )
    )
    assert (await use_case(movies, metadata).execute(REQUEST)).status == "enriched"
    values = movies.update_metadata.call_args.args[1]
    assert (values.title, values.description, values.poster_url) == (
        None,
        "Synopsis",
        "https://fr/poster",
    )
    assert values.trailer_url == "https://fr/first"
    assert values.rating == "G"


@pytest.mark.asyncio
@pytest.mark.parametrize("number", [None, 0, -1, True])
async def test_unusable_values_preserve_source(
    movies: Mock, metadata: Mock, number: int | None
) -> None:
    """Unusable metadata never clears source data."""
    metadata.movie_details.return_value = MetadataBatch(
        (
            MetadataMovie(
                IDENTITY,
                (),
                original_title=" ",
                release_year=number,
                duration_minutes=number,
                localized=(
                    LocalizedMovieMetadata("fr-CA", " ", "", "javascript:bad"),
                    LocalizedMovieMetadata("fr-FR", "No France fallback"),
                ),
                directors=(PersonFact(IDENTITY, " "),),
                genres=(" ",),
                origin_countries=(),
                media=(
                    MovieMedia("https://teaser", "fr", "teaser", True),
                    MovieMedia("https://unofficial", "en", "trailer", False),
                ),
                certifications=(MovieCertification("US", "R"),),
            ),
        )
    )
    assert (await use_case(movies, metadata).execute(REQUEST)).status == "enriched"
    assert movies.update_metadata.call_args.args[1] == MovieMetadataValues()
    assert (await movies.get(REQUEST.movie_id)).values == SOURCE


@pytest.mark.asyncio
async def test_legacy_identity_enriches_once_and_refresh_reuses_policy(
    movies: Mock, metadata: Mock
) -> None:
    """Legacy identity enriches once; explicit refresh fetches again."""
    before = await movies.get(REQUEST.movie_id)
    movies.get.side_effect = None
    movies.get.return_value = replace(before, tmdb_id="123")
    movies.update_metadata.side_effect = None
    case = use_case(movies, metadata)
    assert (await case.execute(REQUEST)).status == "enriched"
    written = movies.update_metadata.call_args.args[1]
    movies.get.return_value = replace(
        before,
        tmdb_id="123",
        metadata_enriched_at=NOW,
        values=replace(before.values, tmdb_vote_count=0),
    )
    assert (await case.execute(REQUEST)).status == "unchanged"
    metadata.movie_details.assert_awaited_once()
    movies.update_metadata.assert_awaited_once()
    refresh = RefreshMoviesUseCase(movies, metadata, lambda: NOW)
    result = await refresh.execute(RefreshMoviesInputData(REQUEST.movie_id))
    assert result.results[0].status == "enriched"
    assert metadata.movie_details.await_count == 2
    assert movies.update_metadata.call_args.args[1] == written


@pytest.mark.asyncio
async def test_stamped_movie_with_null_vote_count_backfills_once(
    movies: Mock, metadata: Mock
) -> None:
    """A prior enrichment stamp does not block the score backfill."""
    before = await movies.get(REQUEST.movie_id)
    stamped = replace(before, tmdb_id="123", metadata_enriched_at=NOW)
    movies.get.side_effect = None
    movies.get.return_value = stamped
    movies.update_metadata.side_effect = None
    case = use_case(movies, metadata)
    assert (await case.execute(REQUEST)).status == "enriched"
    assert movies.update_metadata.call_args.args[1].tmdb_vote_count == 0
    movies.get.return_value = replace(
        stamped, values=replace(stamped.values, tmdb_vote_count=0)
    )
    assert (await case.execute(REQUEST)).status == "unchanged"
    metadata.movie_details.assert_awaited_once_with(IDENTITY)


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["get", "provider", "write", "collision", "clock"])
async def test_failure_preserves_state_and_can_retry(
    movies: Mock, metadata: Mock, stage: str
) -> None:
    """Read, write and validation failures leave enrichment pending."""
    before = await movies.get(REQUEST.movie_id)
    method = {
        "get": movies.get,
        "provider": metadata.movie_details,
        "write": movies.update_metadata,
        "collision": movies.update_metadata,
    }.get(stage)
    original = method.side_effect if method is not None else None
    if method is not None:
        method.side_effect = (
            MovieWorkflowConflictError("collision")
            if stage == "collision"
            else RuntimeError("offline")
        )
    case = (
        EnrichPolicy(movies, metadata, lambda: datetime(2026, 10, 30))
        if stage == "clock"
        else use_case(movies, metadata)
    )
    result = await case.execute(REQUEST)
    assert result.status == "failed"
    assert result.failure is not None
    if method is not None:
        method.side_effect = original
    assert await movies.get(REQUEST.movie_id) == before
    assert (await use_case(movies, metadata).execute(REQUEST)).status == "enriched"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "batch",
    [
        MetadataBatch((), complete=False, failure=MetadataRateLimitedError("Wait")),
        MetadataBatch((), complete=False),
        MetadataBatch(()),
        MetadataBatch((MetadataMovie(IDENTITY, ()), MetadataMovie(IDENTITY, ()))),
        MetadataBatch((MetadataMovie(ProviderIdentity("tmdb", "wrong"), ()),)),
        MetadataBatch(
            (MetadataMovie(IDENTITY, ()),),
            complete=False,
            failure=MetadataUnavailableError("Partial"),
        ),
    ],
)
async def test_invalid_or_incomplete_detail_never_writes(
    movies: Mock, metadata: Mock, batch: MetadataBatch[MetadataMovie]
) -> None:
    """Incomplete, mismatched and failed details cannot stamp success."""
    metadata.movie_details.return_value = batch
    assert (await use_case(movies, metadata).execute(REQUEST)).status == "failed"
    movies.update_metadata.assert_not_awaited()
    assert (await movies.get(REQUEST.movie_id)).metadata_enriched_at is None


@pytest.mark.asyncio
async def test_identity_conflict_and_other_provider_do_not_write(
    movies: Mock, metadata: Mock
) -> None:
    """Other providers never enter tmdb_id and existing identities cannot be stolen."""
    case = use_case(movies, metadata)
    assert (
        await case.execute(replace(REQUEST, identity=ProviderIdentity("other", "123")))
    ).status == "failed"
    before = await movies.get(REQUEST.movie_id)
    movies.get.side_effect = None
    movies.get.return_value = replace(before, tmdb_id="different")
    assert (await case.execute(REQUEST)).status == "failed"
    metadata.movie_details.assert_not_awaited()
    movies.update_metadata.assert_not_awaited()


def test_selection_is_provider_independent() -> None:
    """Equivalent facts select identical values regardless of the provider's label."""
    movie = MetadataMovie(
        IDENTITY, (), localized=(LocalizedMovieMetadata("fr-CA", "Titre"),)
    )
    assert _select_values(movie) == _select_values(
        replace(movie, identity=ProviderIdentity("different", "opaque"))
    )


@pytest.mark.asyncio
async def test_missing_movie_and_unconfirmed_refresh(
    movies: Mock, metadata: Mock
) -> None:
    """Missing and unconfirmed movies report failures without provider lookup."""
    assert (
        await use_case(movies, metadata).execute(replace(REQUEST, movie_id="missing"))
    ).status == "failed"
    refresh = RefreshMoviesUseCase(movies, metadata, lambda: NOW)
    for movie_id in ("missing", REQUEST.movie_id):
        assert (await refresh.execute(RefreshMoviesInputData(movie_id))).results[
            0
        ].status == "failed"
    metadata.movie_details.assert_not_awaited()


@pytest.mark.asyncio
async def test_refresh_all_continues_after_failure_in_stable_order(
    movies: Mock, metadata: Mock
) -> None:
    """Bulk refresh continues after a failure in stable ID order."""
    before = await movies.get(REQUEST.movie_id)
    first = replace(before, movie_id="a", tmdb_id="1", metadata_enriched_at=NOW)
    second = replace(before, movie_id="b", tmdb_id="2", metadata_enriched_at=NOW)
    movies.list_tmdb_movies.return_value = (second, first)
    movies.list_tmdb_movies.side_effect = None
    movies.get.side_effect = {"a": first, "b": second}.get
    movies.update_metadata.side_effect = None
    metadata.movie_details.side_effect = [
        RuntimeError("offline"),
        MetadataBatch((MetadataMovie(ProviderIdentity("tmdb", "2"), ()),)),
    ]
    result = await RefreshMoviesUseCase(movies, metadata, lambda: NOW).execute(
        RefreshMoviesInputData()
    )
    assert [(item.movie_id, item.status) for item in result.results] == [
        ("a", "failed"),
        ("b", "enriched"),
    ]
    assert movies.update_metadata.call_args.args[0] == second
    assert first.metadata_enriched_at == NOW


@pytest.mark.asyncio
async def test_refresh_empty_set(movies: Mock, metadata: Mock) -> None:
    """No confirmed identities produce no fetches or writes."""
    assert (
        await RefreshMoviesUseCase(movies, metadata, lambda: NOW).execute(
            RefreshMoviesInputData()
        )
    ).results == ()
    metadata.movie_details.assert_not_awaited()
    movies.update_metadata.assert_not_awaited()


@pytest.mark.asyncio
async def test_real_fake_skips_import_and_retains_success_on_refresh_failure(
    movies: Mock,
    metadata: Mock,
) -> None:
    """A completed fake write suppresses imports and survives a failed refresh."""
    case = use_case(movies, metadata)
    assert (await case.execute(REQUEST)).status == "enriched"
    saved = await movies.get(REQUEST.movie_id)
    assert (await case.execute(REQUEST)).status == "unchanged"
    metadata.movie_details.assert_awaited_once()
    metadata.movie_details.side_effect = RuntimeError("offline")
    result = await RefreshMoviesUseCase(movies, metadata, lambda: NOW).execute(
        RefreshMoviesInputData(REQUEST.movie_id)
    )
    assert result.results[0].status == "failed"
    assert await movies.get(REQUEST.movie_id) == saved
    movies.update_metadata.assert_awaited_once()


@pytest.mark.asyncio
async def test_single_refresh_read_failure_is_a_failed_result(
    movies: Mock,
    metadata: Mock,
) -> None:
    """A failed single-movie read produces an outcome rather than aborting refresh."""
    movies.get.side_effect = RuntimeError("offline")
    result = await RefreshMoviesUseCase(movies, metadata, lambda: NOW).execute(
        RefreshMoviesInputData(REQUEST.movie_id)
    )
    assert result.results[0].status == "failed"
    assert result.results[0].retryable
    metadata.movie_details.assert_not_awaited()
    movies.update_metadata.assert_not_awaited()


@pytest.mark.parametrize(
    "url",
    [
        "https://bad host/image",
        "https://host:wrong/image",
        "https://[broken",
        "ftp://host/image",
        "/relative",
    ],
)
def test_unusable_urls_are_not_selected(url: str) -> None:
    """Malformed and non-HTTP media URLs preserve source poster and trailer."""
    values = _select_values(
        MetadataMovie(
            IDENTITY,
            (),
            localized=(LocalizedMovieMetadata("fr-CA", poster_url=url),),
            media=(MovieMedia(url, "fr", "trailer", True),),
        )
    )
    assert values.poster_url is None
    assert values.trailer_url is None


@pytest.mark.asyncio
async def test_equivalent_fake_providers_make_identical_use_case_decisions() -> None:
    """Differently named metadata providers select identical patches through execute."""
    patches: list[MovieMetadataValues] = []
    for provider_name in ("TMDB facts", "Independent catalogue facts"):
        provider = create_autospec(
            MetadataRepository, instance=True, name=provider_name
        )
        repository = create_autospec(MovieMetadataRepository, instance=True)
        snapshot = MovieMetadataSnapshot("stable-movie", "revision", SOURCE)
        repository.get.return_value = snapshot
        provider.movie_details.return_value = MetadataBatch(
            (
                MetadataMovie(
                    IDENTITY,
                    (),
                    original_title="Original",
                    duration_minutes=100,
                    localized=(LocalizedMovieMetadata("fr-CA", "Titre"),),
                    media=(MovieMedia("https://media/trailer", "fr", "trailer", True),),
                    certifications=(MovieCertification("CA", "G"),),
                ),
            )
        )
        result = await use_case(repository, provider).execute(REQUEST)
        assert result.status == "enriched"
        provider.movie_details.assert_awaited_once_with(IDENTITY)
        repository.update_metadata.assert_awaited_once()
        expected, patch, tmdb_id, timestamp = repository.update_metadata.call_args.args
        assert (expected, tmdb_id, timestamp) == (snapshot, "123", NOW)
        patches.append(patch)
    assert (
        patches
        == [
            MovieMetadataValues(
                original_title="Original",
                duration_minutes=100,
                trailer_url="https://media/trailer",
                rating="G",
            )
        ]
        * 2
    )


def test_provider_language_poster_is_selected() -> None:
    """A French provider poster is usable even without a regional locale."""
    movie = MetadataMovie(
        IDENTITY,
        (),
        localized=(
            LocalizedMovieMetadata("fr", poster_url="https://example.org/poster.jpg"),
        ),
    )
    assert _select_values(movie).poster_url == "https://example.org/poster.jpg"


def test_canonical_english_title_and_english_poster_are_selected() -> None:
    """TMDB's English title and poster beat translations and other languages."""
    movie = MetadataMovie(
        IDENTITY,
        (
            TitleFact("ゴジラ-1.0", "original", "ja"),
            TitleFact("Godzilla Minus One", "canonical", "en-US"),
        ),
        localized=(
            LocalizedMovieMetadata("fr-CA", "Godzilla Moins Un"),
            LocalizedMovieMetadata("en-US", "English translation"),
            LocalizedMovieMetadata("fr", poster_url="https://example.org/fr.jpg"),
            LocalizedMovieMetadata("und", poster_url="https://example.org/und.jpg"),
            LocalizedMovieMetadata("en", poster_url="https://example.org/en.jpg"),
        ),
    )
    values = _select_values(movie)
    assert values.title == "Godzilla Minus One"
    assert values.poster_url == "https://example.org/en.jpg"


@pytest.mark.asyncio
async def test_title_owned_by_another_film_is_disambiguated_by_year(
    movies: Mock, metadata: Mock
) -> None:
    """A remake's title conflict retries once with the release year appended."""
    update = movies.update_metadata.side_effect
    movies.update_metadata.side_effect = [MovieWorkflowConflictError("taken"), update]
    metadata.movie_details.return_value = MetadataBatch(
        (
            MetadataMovie(
                IDENTITY,
                (TitleFact("Sense and Sensibility", "canonical", "en-US"),),
                release_year=1995,
            ),
        )
    )

    assert (await use_case(movies, metadata).execute(REQUEST)).status == "enriched"
    titles = [call.args[1].title for call in movies.update_metadata.await_args_list]
    assert titles == ["Sense and Sensibility", "Sense and Sensibility (1995)"]
