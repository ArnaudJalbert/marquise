"""Discover and rank movie identities using independent source evidence."""

from __future__ import annotations

import logging
import unicodedata
from dataclasses import dataclass
from typing import Literal

from rapidfuzz.distance import DamerauLevenshtein

from marquise.application.exceptions import (
    MetadataFailure,
    MetadataRateLimitedError,
    MetadataRequestRefusedError,
    MetadataUnavailableError,
    MovieMetadataUnavailableError,
)
from marquise.application.metadata import (
    MatchReason,
    MetadataBatch,
    MetadataMovie,
    MetadataRepository,
    PersonFact,
    ProviderIdentity,
)
from marquise.domain.entities import Movie

logger = logging.getLogger(__name__)

_MAX_CANDIDATE_DETAILS = 5
# Only these stop the cinema. Bad data or a missing record skips one movie.
_OUTAGE_FAILURES = (
    MetadataUnavailableError,
    MetadataRequestRefusedError,
    MetadataRateLimitedError,
)


def _normalize(value: str) -> str:
    return " ".join(
        "".join(
            char
            for char in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(char)
        ).split()
    )


class MatchMoviesUseCase:
    """Select only eligible identities, retaining provider order for true ties."""

    @dataclass(frozen=True, slots=True)
    class MovieInput:
        """Independent source evidence for one movie."""

        title: str
        release_year: int | None = None
        directors: tuple[str, ...] = ()
        duration_minutes: int | None = None
        identity_title: str | None = None
        source_identifier: str | None = None

        def __post_init__(self) -> None:
            if not isinstance(self.title, str):
                raise TypeError("title must be a string")
            if not self.title.strip():
                raise ValueError("Movie title must not be blank")
            self._check_optional(str, "identity_title", "source_identifier")
            self._check_optional(int, "release_year", "duration_minutes")
            if not isinstance(self.directors, tuple):
                raise TypeError("directors must be a tuple")

        def _check_optional(self, expected_type: type, *fields: str) -> None:
            for field in fields:
                value = getattr(self, field)
                if value is not None and not isinstance(value, expected_type):
                    raise TypeError(f"{field} must be a {expected_type.__name__}")

    @dataclass(frozen=True, slots=True)
    class InputData:
        movies: tuple[MatchMoviesUseCase.MovieInput, ...]

        def __post_init__(self) -> None:
            if not isinstance(self.movies, tuple):
                raise TypeError("movies must be a tuple")
            for movie in self.movies:
                if not isinstance(movie, MatchMoviesUseCase.MovieInput):
                    raise TypeError("movies must only contain MovieInput")

    @dataclass(frozen=True, slots=True)
    class MovieMatch:
        """One movie's outcome. A movie with no safe match has no identity."""

        source: MatchMoviesUseCase.MovieInput
        status: Literal["matched", "unmatched", "incomplete"]
        identity: ProviderIdentity | None = None
        titles: tuple[str, ...] = ()
        release_year: int | None = None
        failure: MetadataFailure | None = None

        @property
        def reason(self) -> MatchReason | None:
            """Name why the movie has no identity, or None when it matched."""
            if self.status == "unmatched":
                return "no_match"
            if self.status == "matched":
                return None
            if self.failure is None:
                return "uncertain"
            return type(self.failure).__name__

    @dataclass(frozen=True, slots=True)
    class OutputData:
        matches: tuple[MatchMoviesUseCase.MovieMatch, ...]

    def __init__(self, metadata: MetadataRepository) -> None:
        """Inject discovery without binding policy to a provider."""
        self._metadata = metadata

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
                and DamerauLevenshtein.distance(source, spelling) <= 1
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
        self, source: MovieInput, title: str, movie: MetadataMovie
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

    async def execute(self, input_data: InputData) -> OutputData:
        """Find the provider identity of every movie, one at a time.

        Args:
            input_data: The source evidence for each movie.

        Returns:
            One match per movie, each naming the movie it belongs to. A movie
            with no safe match is an accepted outcome, not an error.

        Raises:
            MovieMetadataUnavailableError: If the provider could not answer.
        """
        matches = [await self._match_one(movie) for movie in input_data.movies]
        logger.info("Matched %d movies", len(matches))
        return self.OutputData(matches=tuple(matches))

    async def _match_one(self, input_data: MovieInput) -> MovieMatch:
        """Search with year, retry unfiltered, then discover through directors.

        Each discovery strategy owns its detail budget and its completeness.
        A confirmed match with the best possible evidence and no unchecked
        earlier candidates cannot be outranked, so it wins even when
        another strategy was truncated. Otherwise a strategy must be exhaustive
        (all relevant candidates hydrated, every page seen) before its winner is
        accepted; a truncated strategy defers to the other strategies and, when
        nothing resolves, reports incomplete rather than unmatched.

        A candidate whose details are bad data or missing is set aside. A
        clear match among the others still wins; otherwise the movie is
        incomplete. Only an outage or rate limit raises.
        """
        title = Movie.search_title(
            (input_data.identity_title or "").strip() or input_data.title
        )
        normalized_title = _normalize(title)
        source_year = input_data.release_year
        candidates: dict[ProviderIdentity, MetadataMovie] = {}
        candidate_order: dict[ProviderIdentity, int] = {}
        director_candidates: set[ProviderIdentity] = set()
        set_aside: set[ProviderIdentity] = set()
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
            seen = set(candidates) | set_aside
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
                if director:
                    director_remaining -= 1
                else:
                    title_remaining -= 1
                if (failure := details.failure) is not None:
                    failures.append(failure)
                    if not isinstance(failure, _OUTAGE_FAILURES):
                        set_aside.add(item.identity)
                        continue
                details_complete = details_complete and details.complete
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

        def decide() -> MatchMoviesUseCase.MovieMatch:
            ranked = [
                (rank, identity)
                for identity, movie in candidates.items()
                if (rank := self._rank(input_data, normalized_title, movie)) is not None
            ]
            outage = next(
                (
                    failure
                    for failure in failures
                    if isinstance(failure, _OUTAGE_FAILURES)
                ),
                None,
            )
            if outage is not None:
                raise MovieMetadataUnavailableError(
                    f"Movie identity failed for '{input_data.title}': "
                    f"{type(outage).__name__}"
                )
            bad_data = failures[0] if failures else None
            if ranked:
                winner_rank, winner_identity = min(
                    ranked, key=lambda pair: (pair[0], candidate_order[pair[1]])
                )
                confirmed = (
                    winner_rank == (0, 0, 0, 0)
                    and bool(input_data.directors)
                    and all(
                        identity in candidates or identity in set_aside
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
                    return self.MovieMatch(
                        input_data,
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
                return self.MovieMatch(input_data, "incomplete", failure=bad_data)
            incomplete = (
                bool(set_aside)
                or not details_complete
                or not title_complete
                or title_budget_exhausted
                or not director_complete
                or director_year_cut
            )
            status = "incomplete" if incomplete else "unmatched"
            logger.info("Movie identity %s for %s", status, input_data.title)
            return self.MovieMatch(input_data, status, failure=bad_data)

        await hydrate(
            await self._metadata.search_movies(title, source_year), director=False
        )
        if (selected := decide()).status == "matched":
            return selected
        if source_year is not None:
            await hydrate(await self._metadata.search_movies(title), director=False)
            if (selected := decide()).status == "matched":
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
