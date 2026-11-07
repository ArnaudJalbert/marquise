"""Deterministic provider-independent acceptance scenarios for #349/#352."""

from dataclasses import replace
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions.movie import MovieMetadataUnavailableError
from marquise.application.metadata import (
    MetadataBatch,
    MetadataFailure,
    MetadataMovie,
    MetadataRepository,
    PersonFact,
    ProviderIdentity,
    TitleFact,
)
from marquise.application.use_cases.match_movies import MatchMoviesUseCase
from marquise.infrastructure.name_distance import RapidFuzzNameDistance

MovieInput = MatchMoviesUseCase.MovieInput


class MatchOneMovie:
    """Run the batch use case for the single movie each scenario describes."""

    def __init__(self, *dependencies: object) -> None:
        self._use_case = MatchMoviesUseCase(*dependencies)

    async def execute(self, movie: MovieInput) -> MatchMoviesUseCase.MovieMatch:
        """Return the only match."""
        output = await self._use_case.execute(self._use_case.InputData((movie,)))
        return output.matches[0]


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
    evidence = MovieInput(source, source_year, directors, runtime + 1)
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(evidence)
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
    result = await MatchOneMovie(
        repository((candidate,)), RapidFuzzNameDistance()
    ).execute(MovieInput("Film", 2026, (source_name,), 100))
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
    result = await MatchOneMovie(
        repository((candidate,)), RapidFuzzNameDistance()
    ).execute(MovieInput("Film", 2026, directors, source_runtime))
    assert (result.status == "matched") == accepted


@pytest.mark.asyncio
async def test_discovery_retry_and_every_director() -> None:
    """La Patrie is found through directed credits after both title searches fail."""
    candidate = movie("Fatherland", directors=(person("Director Name"),))
    repo = repository((candidate,))
    repo.search_movies.return_value = MetadataBatch()
    repo.search_people.return_value = MetadataBatch(candidate.directors)
    repo.directed_movies.return_value = MetadataBatch((candidate, candidate))
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput("La Patrie", 2026, ("Director Name",), 100)
    )
    assert result.identity == candidate.identity
    assert repo.search_movies.await_args_list[1].args == ("La Patrie",)
    repo.movie_details.assert_awaited_once_with(candidate.identity)


@pytest.mark.asyncio
async def test_exact_match_survives_noisy_search() -> None:
    """An exact title, year, and director win despite noisy search results."""
    winner = movie("& Sons", 2026, 119, (person("Pablo Trapero"),), identity="1291829")
    noise = tuple(
        movie(f"{index} & Sons", 2026, 100, (), identity=str(index))
        for index in range(7)
    )
    repo = repository((winner, *noise))
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput("& Sons", 2026, ("Pablo Trapero",), 119)
    )
    assert result.status == "matched"
    assert result.identity == winner.identity


@pytest.mark.asyncio
async def test_director_discovery_survives_noisy_title_search() -> None:
    """A translated title drowned out by noise resolves via director credits."""
    candidate = movie(
        "Fatherland", 2026, 82, (person("Pawel Pawlikowski"),), identity="1437696"
    )
    noise = tuple(
        movie(f"La patrie {index}", 2015 + index, 100, (), identity=str(index))
        for index in range(8)
    )
    repo = repository((candidate, *noise))
    repo.search_movies.side_effect = [MetadataBatch(), MetadataBatch(noise)]
    repo.search_people.return_value = MetadataBatch(candidate.directors)
    repo.directed_movies.return_value = MetadataBatch((candidate,))
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput("La Patrie", 2026, ("Pawel Pawlikowski",), 82)
    )
    assert result.status == "matched"
    assert result.identity == candidate.identity


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
    result = await MatchOneMovie(
        repository(candidates), RapidFuzzNameDistance()
    ).execute(MovieInput("Film", 2026, ("Director Name",), 100))
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
    result = await MatchOneMovie(
        repository((noise, winner)), RapidFuzzNameDistance()
    ).execute(MovieInput("Combattant de rue", 2026))
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
    use_case = MatchOneMovie(repo, RapidFuzzNameDistance())
    if failure:
        with pytest.raises(MovieMetadataUnavailableError):
            await use_case.execute(MovieInput("Film", 2026))
        return
    assert (await use_case.execute(MovieInput("Film", 2026))).status == "incomplete"


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
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput("Le Monde de Wishy", 2026, ("Jens Møller",), 83)
    )
    assert result.identity == candidate.identity
    assert repo.search_movies.await_args_list[1].args == ("Le Monde de Wishy",)


@pytest.mark.asyncio
@pytest.mark.parametrize("year", [None, 2026])
async def test_verity_corroboration(year: int | None) -> None:
    """Verity can pass a year exception only with independent corroboration."""
    candidate = movie("Verity", 2025, 120, (person("Michael Showalter"),))
    use_case = MatchOneMovie(repository((candidate,)), RapidFuzzNameDistance())
    assert (
        await use_case.execute(MovieInput("Verity", year, ("Michael Showalter",), 119))
    ).identity == candidate.identity
    assert (await use_case.execute(MovieInput("Verity", year))).status == "unmatched"


@pytest.mark.asyncio
async def test_carrie_does_not_borrow_candidate_evidence() -> None:
    """An input lacking recovered Carrie evidence cannot confirm a year exception."""
    candidate = movie("Carrie", 1976, 98, (person("Brian De Palma"),))
    result = await MatchOneMovie(
        repository((candidate,)), RapidFuzzNameDistance()
    ).execute(MovieInput("Carrie"))
    assert result.status == "unmatched"


@pytest.mark.asyncio
async def test_discovery_retains_conflicting_codirector() -> None:
    """A credit found through one source director cannot bypass another director."""
    candidate = movie("Fatherland", directors=(person("Director Name"),))
    repo = repository((candidate,))
    repo.search_movies.return_value = MetadataBatch()
    repo.search_people.return_value = MetadataBatch(candidate.directors)
    repo.directed_movies.return_value = MetadataBatch((candidate,))
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput("La Patrie", 2026, ("Director Name", "Other Director"), 100)
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
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput(title, 2026)
    )
    assert result.identity == candidate.identity
    repo.search_movies.assert_awaited_once_with(title, 2026)


def test_rapidfuzz_damerau_distance() -> None:
    """The adapter calculates unrestricted Damerau edits, including short swaps."""
    adapter = RapidFuzzNameDistance()
    assert adapter.distance("ab", "ba") == 1
    assert adapter.distance("ca", "abc") == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("second_credit", [False, True])
async def test_codirectors_require_distinct_people(second_credit: bool) -> None:
    """Two supplied names cannot corroborate a year exception via one person."""
    directors = (person("John Smith"),)
    if second_credit:
        directors += (person("Jon Smith"),)
    candidate = movie(year=2025, directors=directors)
    result = await MatchOneMovie(
        repository((candidate,)), RapidFuzzNameDistance()
    ).execute(MovieInput("Film", 2026, ("John Smith", "Jon Smith"), 100))
    assert (result.status == "matched") == second_credit


@pytest.mark.asyncio
async def test_director_assignment_can_reassign_an_earlier_typo() -> None:
    """A flexible spelling match does not consume another director's only match."""
    candidate = movie(directors=(person("John Smith"), person("Jona Smith")))
    result = await MatchOneMovie(
        repository((candidate,)), RapidFuzzNameDistance()
    ).execute(MovieInput("Film", 2026, ("Jon Smith", "John Smith"), 100))
    assert result.status == "matched"


@pytest.mark.asyncio
async def test_source_identity_title_preserves_screening_title() -> None:
    """Search the film title while retaining the original event label."""
    candidate = movie("Julián", 2025, 85)
    repo = repository((candidate,))
    evidence = MovieInput(
        title="CINEMANIA: Julián",
        release_year=2025,
        duration_minutes=85,
        identity_title="Julián",
    )
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(evidence)
    assert result.identity == candidate.identity
    assert evidence.title == "CINEMANIA: Julián"
    repo.search_movies.assert_awaited_once_with("Julián", 2025)


@pytest.mark.asyncio
async def test_candidate_limit_reports_incomplete() -> None:
    """A bounded search never declares a match while candidates remain unchecked."""
    candidates = tuple(movie(identity=str(i)) for i in range(6))
    repo = repository(candidates)
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput("Film", 2026, (), 100)
    )
    assert result.status == "incomplete"
    assert result.identity is None
    assert repo.movie_details.await_count == 5


@pytest.mark.asyncio
async def test_case_and_screening_labels_do_not_block_a_match() -> None:
    """An uppercase labelled source title matches the provider title."""
    candidate = movie("The Shining", 1980, 146)
    result = await MatchOneMovie(
        repository((candidate,)), RapidFuzzNameDistance()
    ).execute(MovieInput("THE SHINING (anglais avec s.t.f.)", 1980))
    assert result.status == "matched"
    assert result.titles == ("The Shining",)
    assert result.release_year == 1980


@pytest.mark.asyncio
async def test_contained_title_matches_but_ranks_below_an_exact_title() -> None:
    """Containment is a weaker title match; the exact title still wins."""
    longer = movie("Street Fighter: The Legend", identity="longer")
    exact = movie("Street Fighter", identity="exact")
    use_case = MatchOneMovie(repository((longer, exact)), RapidFuzzNameDistance())
    result = await use_case.execute(MovieInput("Street Fighter", 2026))
    assert result.identity == ProviderIdentity("fixture", "exact")
    only = MatchOneMovie(repository((exact,)), RapidFuzzNameDistance())
    contained = await only.execute(
        MovieInput("Street Fighter : le film (version française)", 2026)
    )
    assert contained.identity == ProviderIdentity("fixture", "exact")


@pytest.mark.asyncio
async def test_confirmed_match_does_not_bypass_runtime_ranking() -> None:
    """An unseen exact-runtime candidate prevents a worse confirmed match."""
    candidates = tuple(
        movie(runtime=runtime, directors=(person("Director Name"),), identity=str(i))
        for i, runtime in enumerate((130, 140, 140, 140, 140, 100))
    )
    repo = repository(candidates)
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput("Film", 2026, ("Director Name",), 100)
    )
    assert result.status == "incomplete"
    assert result.identity is None
    assert repo.movie_details.await_count == 5


@pytest.mark.asyncio
@pytest.mark.parametrize("discovery", ["title", "director"])
@pytest.mark.parametrize("directors", [(), ("Director Name",)])
async def test_incomplete_details_do_not_confirm_a_match(
    discovery: str, directors: tuple[str, ...]
) -> None:
    """Partial details remain incomplete even with otherwise perfect evidence."""
    candidate = movie(directors=(person("Director Name"),))
    repo = repository((candidate,))
    if discovery == "director":
        repo.search_movies.return_value = MetadataBatch()
        repo.search_people.return_value = MetadataBatch(candidate.directors)
        repo.directed_movies.return_value = MetadataBatch((candidate,))
    repo.movie_details.side_effect = None
    repo.movie_details.return_value = MetadataBatch((candidate,), complete=False)
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput("Film", 2026, directors, 100)
    )
    expected = "incomplete" if discovery == "title" or directors else "unmatched"
    assert result.status == expected
    assert result.identity is None


@pytest.mark.asyncio
async def test_hydration_priority_preserves_provider_tie_order() -> None:
    """A translation found in details retains the first provider position."""
    first = movie("Other", identity="first")
    second = movie("Film", identity="second")
    repo = repository((first, second))
    translated = replace(first, titles=(TitleFact("Film", "translation"),))
    repo.movie_details.side_effect = lambda identity: MetadataBatch(
        (translated if identity == first.identity else second,)
    )
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput("Film", 2026, (), 100)
    )
    assert result.identity == first.identity
    assert repo.movie_details.await_args_list[0].args == (second.identity,)


@pytest.mark.asyncio
async def test_confirmed_match_waits_for_earlier_provider_candidates() -> None:
    """An unchecked earlier candidate could tie after its titles are hydrated."""
    first = movie("Other", directors=(person("Director Name"),), identity="first")
    exact = tuple(movie(directors=first.directors, identity=str(i)) for i in range(5))
    repo = repository((first, *exact))
    result = await MatchOneMovie(repo, RapidFuzzNameDistance()).execute(
        MovieInput("Film", 2026, ("Director Name",), 100)
    )
    assert result.status == "incomplete"
    assert result.identity is None


@pytest.mark.asyncio
async def test_batch_matches_every_movie_and_names_its_source() -> None:
    """Each result says which movie it belongs to."""
    candidate = movie("Film", 2026, 100)
    use_case = MatchMoviesUseCase(repository((candidate,)), RapidFuzzNameDistance())
    films = (
        MovieInput("Film", 2026, source_identifier="one"),
        MovieInput("Unknown", 2026, source_identifier="two"),
    )
    output = await use_case.execute(use_case.InputData(films))
    assert [match.source for match in output.matches] == list(films)
    assert [match.status for match in output.matches] == ["matched", "unmatched"]


@pytest.mark.parametrize(
    "movies",
    [["Film"], ("Film",)],
)
def test_input_rejects_wrong_types(movies: object) -> None:
    """The batch must be a tuple of movie inputs."""
    with pytest.raises(TypeError):
        MatchMoviesUseCase.InputData(movies=movies)


@pytest.mark.parametrize(
    "fields",
    [
        {"title": 1},
        {"title": "Film", "release_year": "2026"},
        {"title": "Film", "directors": ["Someone"]},
        {"title": "Film", "identity_title": 1},
    ],
)
def test_movie_input_rejects_wrong_types(fields: dict) -> None:
    """Input is the one place types are checked."""
    with pytest.raises(TypeError):
        MovieInput(**fields)
