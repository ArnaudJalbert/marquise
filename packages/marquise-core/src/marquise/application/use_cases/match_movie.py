"""Discover and rank movie identities using independent source evidence."""

import unicodedata
from typing import Protocol

from marquise.application.metadata import (
    MetadataBatch,
    MetadataFailure,
    MetadataMovie,
    MetadataRepository,
    PersonFact,
    ProviderIdentity,
)
from marquise.application.movie_workflows import (
    MatchMovieInputData,
    MatchMovieOutputData,
)
from marquise.domain.entities import Movie

_MAX_CANDIDATE_DETAILS = 5


class NameDistance(Protocol):
    """Injected deterministic Damerau-Levenshtein calculation."""

    def distance(self, left: str, right: str) -> int:
        """Count edits, including an adjacent swap as one edit."""
        ...


def _normalize(value: str) -> str:
    return " ".join(
        "".join(
            char
            for char in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(char)
        ).split()
    )


class MatchMovieUseCase:
    """Select only eligible identities, retaining provider order for true ties."""

    def __init__(self, metadata: MetadataRepository, distance: NameDistance) -> None:
        """Inject discovery and distance without binding policy to a provider."""
        self._metadata = metadata
        self._distance = distance

    def _person_match(self, name: str, person: PersonFact) -> int | None:
        source = _normalize(name)
        if not source:
            return None
        spellings = tuple(_normalize(value) for value in (person.name, *person.aliases))
        if source in spellings:
            return 0
        for spelling in spellings:
            if (
                sum(char.isalpha() for char in source) >= 8
                and sum(char.isalpha() for char in spelling) >= 8
                and self._distance.distance(source, spelling) <= 1
            ):
                return 1
        return None

    def _director_spelling(
        self, names: tuple[str, ...], people: tuple[PersonFact, ...]
    ) -> int | None:
        edges = [
            [
                (person.identity, match)
                for person in people
                if (match := self._person_match(name, person)) is not None
            ]
            for name in names
        ]

        def assign(exact_only: bool) -> bool:
            assigned: dict[ProviderIdentity, int] = {}

            def visit(index: int, seen: set[ProviderIdentity]) -> bool:
                for identity, match in edges[index]:
                    if identity in seen or (exact_only and match != 0):
                        continue
                    seen.add(identity)
                    if identity not in assigned or visit(assigned[identity], seen):
                        assigned[identity] = index
                        return True
                return False

            return all(visit(index, set()) for index in range(len(names)))

        if assign(exact_only=True):
            return 0
        return 1 if assign(exact_only=False) else None

    def _rank(
        self, source: MatchMovieInputData, title: str, movie: MetadataMovie
    ) -> tuple[int, int, int, float] | None:
        title_tier = self._title_tier(title, movie)
        title_match = title_tier < 2
        year_match = (
            source.release_year is not None
            and source.release_year == movie.release_year
        )
        spelling = self._director_spelling(source.directors, movie.directors)
        if spelling is None:
            return None
        directors_agree = bool(source.directors)
        runtime = float("inf")
        if (
            source.duration_minutes is not None
            and source.duration_minutes > 0
            and movie.duration_minutes is not None
            and movie.duration_minutes > 0
        ):
            runtime = abs(source.duration_minutes - movie.duration_minutes)
        if title_match and year_match:
            if runtime != float("inf") and runtime > 10 and not directors_agree:
                return None
        elif title_match:
            if not directors_agree or runtime > 10:
                return None
        elif not (year_match and directors_agree and runtime <= 10):
            return None
        return (
            title_tier,
            int(not year_match),
            spelling,
            runtime,
        )

    @staticmethod
    def _title_tier(title: str, movie: MetadataMovie) -> int:
        """0 for the same title, 1 when one contains the other, 2 otherwise."""
        if not title:
            return 2
        values = [
            value
            for value in (
                *(fact.title for fact in movie.titles),
                movie.original_title or "",
            )
            if value.strip()
        ]
        key = Movie.title_key(title)
        if any(
            _normalize(value) == title or Movie.title_key(value) == key
            for value in values
        ):
            return 0
        return 1 if any(Movie.titles_overlap(title, value) for value in values) else 2

    async def execute(self, input_data: MatchMovieInputData) -> MatchMovieOutputData:
        """Search with year, retry unfiltered, then discover through directors.

        Each discovery strategy owns its detail budget and its completeness.
        A confirmed match with the best possible evidence and no unchecked
        earlier candidates cannot be outranked, so it wins even when
        another strategy was truncated. Otherwise a strategy must be exhaustive
        (all relevant candidates hydrated, every page seen) before its winner is
        accepted; a truncated strategy defers to the other strategies and, when
        nothing resolves, reports incomplete rather than unmatched.
        """
        title = Movie.search_title(
            (input_data.identity_title or "").strip() or input_data.title
        )
        normalized_title = _normalize(title)
        source_year = input_data.release_year
        candidates: dict[ProviderIdentity, MetadataMovie] = {}
        candidate_order: dict[ProviderIdentity, int] = {}
        director_candidates: set[ProviderIdentity] = set()
        details_complete = True
        failures: list[MetadataFailure] = []
        title_complete = True
        director_complete = True
        title_remaining = _MAX_CANDIDATE_DETAILS
        director_remaining = _MAX_CANDIDATE_DETAILS
        title_budget_exhausted = False
        director_year_cut = False

        async def hydrate(
            batch: MetadataBatch[MetadataMovie], *, director: bool
        ) -> None:
            nonlocal title_complete, director_complete, details_complete
            nonlocal title_remaining, director_remaining
            nonlocal title_budget_exhausted, director_year_cut
            if director:
                director_complete = director_complete and batch.complete
            else:
                title_complete = title_complete and batch.complete
            if batch.failure is not None:
                failures.append(batch.failure)
            seen = set(candidates)
            pending: list[tuple[int, MetadataMovie]] = []
            for index, item in enumerate(batch.items):
                candidate_order.setdefault(item.identity, len(candidate_order))
                if item.identity not in seen:
                    seen.add(item.identity)
                    pending.append((index, item))
            pending.sort(
                key=lambda pair: (
                    self._title_tier(normalized_title, pair[1]),
                    not (
                        source_year is not None and pair[1].release_year == source_year
                    ),
                    pair[0],
                )
            )
            for position, (_, item) in enumerate(pending):
                remaining = director_remaining if director else title_remaining
                if remaining == 0:
                    if director and source_year is not None:
                        director_year_cut = director_year_cut or any(
                            movie.release_year == source_year
                            for _, movie in pending[position:]
                        )
                    else:
                        title_budget_exhausted = True
                    break
                details = await self._metadata.movie_details(item.identity)
                details_complete = details_complete and details.complete
                if details.failure is not None:
                    failures.append(details.failure)
                hydrated = next(
                    (
                        detail
                        for detail in details.items
                        if detail.identity == item.identity
                    ),
                    item,
                )
                candidates[item.identity] = hydrated
                if director:
                    director_candidates.add(item.identity)
                    director_remaining -= 1
                else:
                    title_remaining -= 1

        def decide() -> MatchMovieOutputData:
            ranked = [
                (rank, identity)
                for identity, movie in candidates.items()
                if (rank := self._rank(input_data, normalized_title, movie)) is not None
            ]
            if failures:
                return MatchMovieOutputData("failed", failure=failures[0])
            if ranked:
                winner_rank, winner_identity = min(
                    ranked, key=lambda pair: (pair[0], candidate_order[pair[1]])
                )
                confirmed = (
                    winner_rank == (0, 0, 0, 0)
                    and bool(input_data.directors)
                    and all(
                        identity in candidates
                        for identity, order in candidate_order.items()
                        if order < candidate_order[winner_identity]
                    )
                )
                if winner_identity in director_candidates:
                    complete = director_complete and not director_year_cut
                else:
                    complete = title_complete and not title_budget_exhausted
                if details_complete and (confirmed or complete):
                    chosen = candidates[winner_identity]
                    return MatchMovieOutputData(
                        "matched",
                        winner_identity,
                        titles=tuple(
                            dict.fromkeys(
                                value
                                for value in (
                                    *(fact.title for fact in chosen.titles),
                                    chosen.original_title or "",
                                )
                                if value.strip()
                            )
                        ),
                        release_year=chosen.release_year,
                    )
                return MatchMovieOutputData("incomplete")
            incomplete = (
                not details_complete
                or not title_complete
                or title_budget_exhausted
                or not director_complete
                or director_year_cut
            )
            return MatchMovieOutputData("incomplete" if incomplete else "unmatched")

        await hydrate(
            await self._metadata.search_movies(title, source_year), director=False
        )
        if (selected := decide()).status in ("matched", "failed"):
            return selected
        if source_year is not None:
            await hydrate(await self._metadata.search_movies(title), director=False)
            if (selected := decide()).status in ("matched", "failed"):
                return selected
        seen_people: set[ProviderIdentity] = set()
        for name in input_data.directors:
            people = await self._metadata.search_people(name)
            if people.failure is not None:
                failures.append(people.failure)
            director_complete = director_complete and people.complete
            for person in people.items:
                if (
                    person.identity in seen_people
                    or self._person_match(name, person) is None
                ):
                    continue
                seen_people.add(person.identity)
                await hydrate(
                    await self._metadata.directed_movies(person.identity),
                    director=True,
                )
        return decide()
