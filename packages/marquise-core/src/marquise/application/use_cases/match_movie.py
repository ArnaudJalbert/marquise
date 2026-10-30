"""Discover and rank movie identities using independent source evidence."""

import re
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


def _search_title(title: str) -> str:
    # Strip only complete, trailing screening labels, never arbitrary parentheses.
    language = (
        r"(?:fran[cç]ais(?:e)?|anglais(?:e)?|english|french|"
        r"tamil|tamoul|punjabi|pendjabi|espagnol(?:e)?|spanish)"
    )
    label = (
        rf"(?:version\s+{language}|{language}\s+(?:w/e\.s\.t\.|s\.t\.f\.)|"
        r"TAM\.ENG\.SUB|\d+(?:e|er|th)?\s+anniversaire)"
    )
    pattern = rf"(?:\s*\(\s*{label}\s*\)|\s*[:\-]\s*{label}|\s+{label})\s*$"
    while True:
        cleaned = re.sub(pattern, "", title, flags=re.IGNORECASE).strip()
        if cleaned == title:
            return cleaned
        title = cleaned


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

    def _rank(
        self, source: MatchMovieInputData, title: str, movie: MetadataMovie
    ) -> tuple[int, int, int, float] | None:
        title_match = bool(title) and title in {
            _normalize(value)
            for value in (
                *(fact.title for fact in movie.titles),
                movie.original_title or "",
            )
            if value.strip()
        }
        year_match = (
            source.release_year is not None
            and source.release_year == movie.release_year
        )
        matches = [
            min(
                (
                    match
                    for person in movie.directors
                    if (match := self._person_match(name, person)) is not None
                ),
                default=None,
            )
            for name in source.directors
        ]
        if any(match is None for match in matches):
            return None
        directors_agree = bool(matches)
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
            int(not title_match),
            int(not year_match),
            int(any(match == 1 for match in matches)),
            runtime,
        )

    async def execute(self, input_data: MatchMovieInputData) -> MatchMovieOutputData:
        """Search with year, retry unfiltered, then discover through directors.

        Each stage is ranked together. Partial retrieval cannot establish the
        best candidate, even if a returned candidate would otherwise qualify.
        """
        title = _search_title(input_data.title)
        batches: list[MetadataBatch[MetadataMovie] | MetadataBatch[PersonFact]] = []
        candidates: dict[ProviderIdentity, MetadataMovie] = {}

        async def collect(batch: MetadataBatch[MetadataMovie]) -> None:
            batches.append(batch)
            for item in batch.items:
                if item.identity in candidates:
                    continue
                details = await self._metadata.movie_details(item.identity)
                batches.append(details)
                candidates[item.identity] = next(
                    (
                        detail
                        for detail in details.items
                        if detail.identity == item.identity
                    ),
                    item,
                )

        def result() -> MatchMovieOutputData | None:
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
            return MatchMovieOutputData(
                "matched", min(ranked, key=lambda pair: pair[0])[1]
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
