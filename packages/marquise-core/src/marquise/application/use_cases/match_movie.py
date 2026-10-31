"""Discover and rank movie identities using independent source evidence."""

import unicodedata
from typing import Protocol

from marquise.application.metadata import (
    MetadataBatch,
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

        Each stage is ranked together. Partial retrieval cannot establish the
        best candidate, even if a returned candidate would otherwise qualify.
        """
        title = Movie.search_title(
            (input_data.identity_title or "").strip() or input_data.title
        )
        batches: list[MetadataBatch[MetadataMovie] | MetadataBatch[PersonFact]] = []
        candidates: dict[ProviderIdentity, MetadataMovie] = {}
        candidate_details_remaining = _MAX_CANDIDATE_DETAILS
        candidate_limit_reached = False

        async def collect(batch: MetadataBatch[MetadataMovie]) -> None:
            nonlocal candidate_details_remaining, candidate_limit_reached
            batches.append(batch)
            seen = set(candidates)
            pending = []
            for index, item in enumerate(batch.items):
                if item.identity not in seen:
                    seen.add(item.identity)
                    pending.append((index, item))
            pending.sort(
                key=lambda pair: (
                    self._title_tier(_normalize(title), pair[1]),
                    not (
                        input_data.release_year is not None
                        and pair[1].release_year == input_data.release_year
                    ),
                    pair[0],
                )
            )
            hydrated: dict[ProviderIdentity, MetadataMovie] = {}
            for _, item in pending:
                if candidate_details_remaining == 0:
                    candidate_limit_reached = True
                    break
                details = await self._metadata.movie_details(item.identity)
                batches.append(details)
                candidate_details_remaining -= 1
                hydrated[item.identity] = next(
                    (
                        detail
                        for detail in details.items
                        if detail.identity == item.identity
                    ),
                    item,
                )
            for _, item in sorted(pending, key=lambda pair: pair[0]):
                if item.identity in hydrated:
                    candidates[item.identity] = hydrated[item.identity]

        def result() -> MatchMovieOutputData | None:
            if candidate_limit_reached:
                failure = next(
                    (batch.failure for batch in batches if batch.failure), None
                )
                if failure:
                    return MatchMovieOutputData("failed", failure=failure)
                return MatchMovieOutputData("incomplete")
            ranked = [
                (rank, movie.identity)
                for movie in candidates.values()
                if (rank := self._rank(input_data, _normalize(title), movie))
                is not None
            ]
            if not ranked:
                return None
            failure = next((batch.failure for batch in batches if batch.failure), None)
            if failure:
                return MatchMovieOutputData("failed", failure=failure)
            if any(not batch.complete for batch in batches):
                return MatchMovieOutputData("incomplete")
            identity = min(ranked, key=lambda pair: pair[0])[1]
            chosen = candidates[identity]
            return MatchMovieOutputData(
                "matched",
                identity,
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

        await collect(
            await self._metadata.search_movies(title, input_data.release_year)
        )
        if selected := result():
            return selected
        if input_data.release_year is not None:
            await collect(await self._metadata.search_movies(title))
            if selected := result():
                return selected
        seen_people: set[ProviderIdentity] = set()
        for name in input_data.directors:
            people = await self._metadata.search_people(name)
            batches.append(people)
            for person in people.items:
                if (
                    person.identity in seen_people
                    or self._person_match(name, person) is None
                ):
                    continue
                seen_people.add(person.identity)
                await collect(await self._metadata.directed_movies(person.identity))
        if selected := result():
            return selected
        failure = next((batch.failure for batch in batches if batch.failure), None)
        if failure:
            return MatchMovieOutputData("failed", failure=failure)
        return MatchMovieOutputData(
            "incomplete"
            if any(not batch.complete for batch in batches)
            else "unmatched"
        )
