# Use case rules

Read when creating, changing or reviewing a use case or query under `packages/marquise-core/src/marquise/application/`.

These rules take precedence over ponytail. When they pull apart, follow these rules, even if the diff gets longer.

| Rules | Covers |
|---|---|
| [dependencies](use-cases/dependencies.md) | Required dependencies, injecting use cases, self-containment |
| [structure](use-cases/structure.md) | One job per use case, private members, the top-down call tree |
| [input-and-output](use-cases/input-and-output.md) | Inner `InputData` and `OutputData`, type checks |
| [failure](use-cases/failure.md) | No fallbacks, raising exceptions, accepted outcomes, safe reruns |
| [logging](use-cases/logging.md) | What to log and at which level |
| [testing](use-cases/testing.md) | Testing through `execute` with autospec mocks |

Functions follow [functions](functions.md).

## Complete example

A use case that follows every rule. `TitleMatcher` is a made-up interface. A coordinating use case is shown in [structure](use-cases/structure.md#responsibility).

```python
"""Command use case: find or create the movies a cinema shows."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from marquise.application.exceptions.cinema import CinemaNotFoundError
from marquise.application.repositories import (
    CinemaRepository,
    MovieRepository,
    TitleMatcher,
)
from marquise.domain.entities import Movie
from marquise.domain.value_objects import CinemaId, MovieId

logger = logging.getLogger(__name__)


class AddCinemaMoviesCommand:
    """Find or create one movie for each title a cinema shows."""

    @dataclass(frozen=True, slots=True)
    class InputData:
        cinema_id: str
        titles: tuple[str, ...]

        def __post_init__(self) -> None:
            if not isinstance(self.cinema_id, str):
                raise TypeError("cinema_id must be a string")
            if not isinstance(self.titles, tuple):
                raise TypeError("titles must be a tuple")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        movie_ids: tuple[str, ...]

    @dataclass(frozen=True, slots=True)
    class MatchedTitle:
        title: str
        tmdb_id: str

    def __init__(
        self,
        cinema_repository: CinemaRepository,
        movie_repository: MovieRepository,
        title_matcher: TitleMatcher,
    ) -> None:
        self._cinema_repository = cinema_repository
        self._movie_repository = movie_repository
        self._title_matcher = title_matcher

    async def execute(self, input_data: InputData) -> OutputData:
        """Find or create one movie for each title a cinema shows.

        Args:
            input_data: The cinema and the titles it shows.

        Returns:
            The ID of the movie behind each title.

        Raises:
            CinemaNotFoundError: If the cinema does not exist.
        """
        await self._require_cinema(input_data.cinema_id)
        movies = await self._resolve_all(input_data.titles)
        logger.info("Added %d movies for %s", len(movies), input_data.cinema_id)
        return self.OutputData(movie_ids=tuple(movie.id.value for movie in movies))

    async def _require_cinema(self, cinema_id: str) -> None:
        cinema = await self._cinema_repository.find_by_id(CinemaId(cinema_id))
        if cinema is None:
            raise CinemaNotFoundError(f"Cinema '{cinema_id}' not found")

    async def _resolve_all(self, titles: tuple[str, ...]) -> list[Movie]:
        return [await self._resolve_title(title) for title in titles]

    async def _resolve_title(self, title: str) -> Movie:
        logger.debug("Resolving title %s", title)
        # A TMDB outage raises here and stops the use case.
        tmdb_id = await self._title_matcher.find_tmdb_id(title)
        # No match is an accepted outcome, so it has its own path.
        if tmdb_id is None:
            logger.info("No TMDB match for %s", title)
            return await self._create_unmatched_movie(title)
        matched = self.MatchedTitle(title, tmdb_id)
        return await self._find_or_create_matched_movie(matched)

    async def _create_unmatched_movie(self, title: str) -> Movie:
        movie = Movie(id=MovieId(value=uuid4().hex), title=title)
        return await self._movie_repository.create_or_reuse(movie)

    async def _find_or_create_matched_movie(self, matched: MatchedTitle) -> Movie:
        existing = await self._movie_repository.find_by_tmdb_id(matched.tmdb_id)
        if existing is None:
            return await self._create_matched_movie(matched)
        return existing

    async def _create_matched_movie(self, matched: MatchedTitle) -> Movie:
        movie = Movie(
            id=MovieId(value=uuid4().hex),
            title=matched.title,
            tmdb_id=matched.tmdb_id,
        )
        return await self._movie_repository.create_or_reuse(movie)
```
