"""Deterministic provider-independent acceptance scenarios for #349/#352."""

from dataclasses import replace
from unittest.mock import create_autospec

import pytest

from marquise.application.metadata import (
    MetadataBatch,
    MetadataFailure,
    MetadataMovie,
    MetadataRepository,
    PersonFact,
    ProviderIdentity,
    TitleFact,
)
from marquise.application.movie_workflows import MatchMovieInputData
from marquise.application.use_cases.match_movie import MatchMovieUseCase
from marquise.infrastructure.name_distance import RapidFuzzNameDistance


def person(name: str, aliases: tuple[str, ...] = ()) -> PersonFact:
    """Build verified person evidence without a live provider."""
    return PersonFact(ProviderIdentity("fixture", name), name, aliases)


def movie(
    title: str = "Film",
    year: int | None = 2026,
    runtime: int | None = 100,
    directors: tuple[PersonFact, ...] = (),
    identity: str = "winner",
) -> MetadataMovie:
    """Build ordered candidate facts."""
    return MetadataMovie(
        ProviderIdentity("fixture", identity),
        (TitleFact(title, "canonical"),),
        year,
        runtime,
        directors,
    )


def repository(candidates: tuple[MetadataMovie, ...]) -> MetadataRepository:
    """Autospec discovery and return complete candidate details."""
    repo = create_autospec(MetadataRepository, instance=True)
    repo.search_movies.return_value = MetadataBatch(candidates)
    repo.search_people.return_value = MetadataBatch()
    repo.directed_movies.return_value = MetadataBatch()
    repo.movie_details.side_effect = lambda identity: MetadataBatch(
        tuple(item for item in candidates if item.identity == identity)
    )
    return repo


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source,title,year,runtime,directors",
    [
        ("Fjord (Version française)", "Fjord", 2026, 100, ()),
        ("Jailer 2 TAM.ENG.SUB", "Jailer 2", 2026, 163, ()),
        ("Patakka Guddiyan (Punjabi w/e.s.t.)", "Patakka Guddiyan", 2026, 127, ()),
        (
            "La Bola Negra (Espagnol s.t.f.)",
            "La Bola Negra",
            2026,
            159,
            ("Javier Calvo", "Javier Ambrossi"),
        ),
        ("Rembrandt (Français s.t.f.)", "Rembrandt", 2025, 107, ("Pierre Schoeller",)),
        ("Le Monde de Wishy", "Le Monde de Wishy", 2025, 83, ("Jens Møller",)),
        ("Vous pouvez tout voir", "Vous pouvez tout voir", 2026, 174, ()),
        ("Udta Teer", "Udta Teer", 2026, 100, ("Akash A Kaushik",)),
        ("Carrie", "Carrie", 1976, 98, ("Brian De Palma",)),
        ("The Fly: 40e anniversaire", "The Fly", 1986, 96, ()),
        ("Faust: 100e anniversaire", "Faust", 1926, 107, ()),
        ("Film (Meaningful)", "Film (Meaningful)", 2026, 100, ()),
    ],
)
async def test_acceptance_examples(
    source: str, title: str, year: int, runtime: int, directors: tuple[str, ...]
) -> None:
    """Recognized labels and recovered source evidence select the expected film."""
    facts = tuple(person(name) for name in directors)
    if source == "Udta Teer":
        facts = (person("Aakash Kaushik", ("Akash A Kaushik",)),)
    candidate = movie(title, year, runtime, facts)
    if source in ("Le Monde de Wishy", "Vous pouvez tout voir"):
        candidate = replace(
            candidate,
            titles=(
                TitleFact("Other", "canonical"),
                TitleFact(title, "translation", "fr-CA"),
            ),
        )
    repo = repository((candidate,))
    source_year = 2026 if source.startswith(("Rembrandt", "Le Monde")) else year
    evidence = MatchMovieInputData(source, source_year, directors, runtime + 1)
    result = await MatchMovieUseCase(repo, RapidFuzzNameDistance()).execute(evidence)
    assert result.identity == candidate.identity
    assert evidence.title == source
    repo.search_movies.assert_any_await(title, source_year)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_name,canonical,accepted",
    [
        ("Brian De Plama", "Brian De Palma", True),
        ("brián  de palma", "Brian De Palma", True),
        ("John Wo", "John Wu", False),
        ("John Woo", "John Woo", True),
        ("Brian De Pxxma", "Brian De Palma", False),
        ("Javier Calvo and Javier Ambrossi", "Javier Calvo", False),
    ],
)
async def test_director_spelling(
    source_name: str, canonical: str, accepted: bool
) -> None:
    """Only long names tolerate one edit; source co-directors are never split here."""
    candidate = movie(directors=(person(canonical), person("Extra Director")))
    result = await MatchMovieUseCase(
        repository((candidate,)), RapidFuzzNameDistance()
    ).execute(MatchMovieInputData("Film", 2026, (source_name,), 100))
    assert (result.status == "matched") == accepted


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "title,year,directors,source_runtime,runtime,accepted",
    [
        ("Film", 2026, (), None, 100, True),
        ("Film", 2026, (), 0, 100, True),
        ("Film", 2026, (), 100, 111, False),
        ("Film", 2026, ("Director Name",), 100, 130, True),
        ("Film", 2025, (), 100, 100, False),
        ("Film", None, ("Director Name",), 100, 110, True),
        ("Film", 2025, ("Director Name",), 100, 111, False),
        ("Film", 2025, ("Director Name",), None, 100, False),
        ("Other", 2026, ("Director Name",), 100, 110, True),
        ("Other", 2025, ("Director Name",), 100, 100, False),
        ("Other", 2026, (), 100, 100, False),
        ("Film", 2026, ("Wrong Director",), 100, 100, False),
    ],
)
async def test_eligibility(
    title: str,
    year: int | None,
    directors: tuple[str, ...],
    source_runtime: int | None,
    runtime: int,
    accepted: bool,
) -> None:
    """Year and runtime exceptions require independent director corroboration."""
    candidate = movie(title, year, runtime, (person("Director Name"),))
    result = await MatchMovieUseCase(
        repository((candidate,)), RapidFuzzNameDistance()
    ).execute(MatchMovieInputData("Film", 2026, directors, source_runtime))
    assert (result.status == "matched") == accepted


@pytest.mark.asyncio
async def test_discovery_retry_and_every_director() -> None:
    """La Patrie is found through directed credits after both title searches fail."""
    candidate = movie("Fatherland", directors=(person("Director Name"),))
    repo = repository((candidate,))
    repo.search_movies.return_value = MetadataBatch()
    repo.search_people.return_value = MetadataBatch(candidate.directors)
    repo.directed_movies.return_value = MetadataBatch((candidate, candidate))
    result = await MatchMovieUseCase(repo, RapidFuzzNameDistance()).execute(
        MatchMovieInputData("La Patrie", 2026, ("Director Name",), 100)
    )
    assert result.identity == candidate.identity
    assert repo.search_movies.await_args_list[1].args == ("La Patrie",)
    repo.movie_details.assert_awaited_once_with(candidate.identity)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dimension", ["title", "year", "spelling", "runtime", "unknown", "tie"]
)
async def test_lexicographic_ranking(dimension: str) -> None:
    """Earlier evidence wins; exact ties retain provider order."""
    winner = movie(directors=(person("Director Name"),))
    loser = replace(winner, identity=ProviderIdentity("fixture", "loser"))
    if dimension == "title":
        loser = replace(loser, titles=(TitleFact("Other", "canonical"),))
    elif dimension == "year":
        loser = replace(loser, release_year=2025)
    elif dimension == "spelling":
        loser = replace(loser, directors=(person("Director Nmae"),))
    elif dimension == "runtime":
        loser = replace(loser, duration_minutes=101)
    elif dimension == "unknown":
        loser = replace(loser, duration_minutes=None)
    candidates = (winner, loser) if dimension == "tie" else (loser, winner)
    result = await MatchMovieUseCase(
        repository(candidates), RapidFuzzNameDistance()
    ).execute(MatchMovieInputData("Film", 2026, ("Director Name",), 100))
    assert result.identity == winner.identity


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["tmdb", "another-provider"])
async def test_provider_equivalence_and_search_noise(provider: str) -> None:
    """Equivalent verified French aliases win despite unrelated search noise."""
    winner = replace(
        movie("Street Fighter"),
        identity=ProviderIdentity(provider, "42"),
        titles=(
            TitleFact("Street Fighter", "original"),
            TitleFact("Combattant de rue", "alternative"),
        ),
    )
    noise = replace(
        movie("Street Fighter II"), identity=ProviderIdentity(provider, "noise")
    )
    result = await MatchMovieUseCase(
        repository((noise, winner)), RapidFuzzNameDistance()
    ).execute(MatchMovieInputData("Combattant de rue", 2026))
    assert result.identity == ProviderIdentity(provider, "42")


@pytest.mark.asyncio
@pytest.mark.parametrize("has_candidate", [False, True])
@pytest.mark.parametrize(
    "failure", [None, MetadataFailure("rate_limited", "retry", True)]
)
async def test_partial_discovery(
    has_candidate: bool, failure: MetadataFailure | None
) -> None:
    """Partial searches neither prove absence nor guarantee the best candidate."""
    candidate = movie()
    repo = repository((candidate,))
    repo.search_movies.return_value = MetadataBatch(
        (candidate,) if has_candidate else (), complete=False, failure=failure
    )
    result = await MatchMovieUseCase(repo, RapidFuzzNameDistance()).execute(
        MatchMovieInputData("Film", 2026)
    )
    assert result.status == ("failed" if failure else "incomplete")
    assert result.failure == failure


@pytest.mark.asyncio
async def test_detail_only_translation_and_unfiltered_retry() -> None:
    """Search summaries lack the translation that movie details verify."""
    candidate = movie("Fleak", 2025, 83, (person("Jens Møller"),))
    repo = repository((candidate,))
    repo.search_movies.side_effect = [MetadataBatch(), MetadataBatch((candidate,))]
    repo.movie_details.side_effect = None
    repo.movie_details.return_value = MetadataBatch(
        (
            replace(
                candidate,
                titles=(
                    *candidate.titles,
                    TitleFact("Le Monde de Wishy", "translation"),
                ),
            ),
        )
    )
    result = await MatchMovieUseCase(repo, RapidFuzzNameDistance()).execute(
        MatchMovieInputData("Le Monde de Wishy", 2026, ("Jens Møller",), 83)
    )
    assert result.identity == candidate.identity
    assert repo.search_movies.await_args_list[1].args == ("Le Monde de Wishy",)


@pytest.mark.asyncio
@pytest.mark.parametrize("year", [None, 2026])
async def test_verity_corroboration(year: int | None) -> None:
    """Verity can pass a year exception only with independent corroboration."""
    candidate = movie("Verity", 2025, 120, (person("Michael Showalter"),))
    use_case = MatchMovieUseCase(repository((candidate,)), RapidFuzzNameDistance())
    assert (
        await use_case.execute(
            MatchMovieInputData("Verity", year, ("Michael Showalter",), 119)
        )
    ).identity == candidate.identity
    assert (
        await use_case.execute(MatchMovieInputData("Verity", year))
    ).status == "unmatched"


@pytest.mark.asyncio
async def test_carrie_does_not_borrow_candidate_evidence() -> None:
    """An input lacking recovered Carrie evidence cannot confirm a year exception."""
    candidate = movie("Carrie", 1976, 98, (person("Brian De Palma"),))
    result = await MatchMovieUseCase(
        repository((candidate,)), RapidFuzzNameDistance()
    ).execute(MatchMovieInputData("Carrie"))
    assert result.status == "unmatched"


@pytest.mark.asyncio
async def test_discovery_retains_conflicting_codirector() -> None:
    """A credit found through one source director cannot bypass another director."""
    candidate = movie("Fatherland", directors=(person("Director Name"),))
    repo = repository((candidate,))
    repo.search_movies.return_value = MetadataBatch()
    repo.search_people.return_value = MetadataBatch(candidate.directors)
    repo.directed_movies.return_value = MetadataBatch((candidate,))
    result = await MatchMovieUseCase(repo, RapidFuzzNameDistance()).execute(
        MatchMovieInputData("La Patrie", 2026, ("Director Name", "Other Director"), 100)
    )
    assert result.status == "unmatched"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "title",
    [
        "Film: a celebration",
        "Film (Director's Cut)",
        "Film: anniversaire",
        "Film 40e anniversaire edition",
    ],
)
async def test_meaningful_suffixes_are_preserved(title: str) -> None:
    """Arbitrary event labels and meaningful parentheses remain identity text."""
    candidate = movie(title)
    repo = repository((candidate,))
    result = await MatchMovieUseCase(repo, RapidFuzzNameDistance()).execute(
        MatchMovieInputData(title, 2026)
    )
    assert result.identity == candidate.identity
    repo.search_movies.assert_awaited_once_with(title, 2026)


def test_rapidfuzz_damerau_distance() -> None:
    """The adapter calculates unrestricted Damerau edits, including short swaps."""
    adapter = RapidFuzzNameDistance()
    assert adapter.distance("ab", "ba") == 1
    assert adapter.distance("ca", "abc") == 2
