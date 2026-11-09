"""Query: find the stored movie each fetched screening belongs to."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from marquise.application.exceptions.movie import MovieNotLinkedError

logger = logging.getLogger(__name__)


class LinkScreeningsQuery:
    """Link each screening to its movie by title and source identifier.

    Titles are compared ignoring case and spacing, because sources vary them.
    """

    @dataclass(frozen=True, slots=True)
    class ScreeningInput:
        movie_title: str
        source_identifier: str | None = None

        def __post_init__(self) -> None:
            if not isinstance(self.movie_title, str):
                raise TypeError("movie_title must be a string")
            if self.source_identifier is not None and not isinstance(
                self.source_identifier, str
            ):
                raise TypeError("source_identifier must be a string")

    @dataclass(frozen=True, slots=True)
    class MovieInput:
        title: str
        movie_id: str
        source_identifier: str | None = None

        def __post_init__(self) -> None:
            if not isinstance(self.title, str):
                raise TypeError("title must be a string")
            if not isinstance(self.movie_id, str):
                raise TypeError("movie_id must be a string")
            if self.source_identifier is not None and not isinstance(
                self.source_identifier, str
            ):
                raise TypeError("source_identifier must be a string")

    @dataclass(frozen=True, slots=True)
    class InputData:
        screenings: tuple[LinkScreeningsQuery.ScreeningInput, ...]
        movies: tuple[LinkScreeningsQuery.MovieInput, ...]

        def __post_init__(self) -> None:
            if not isinstance(self.screenings, tuple):
                raise TypeError("screenings must be a tuple")
            if not isinstance(self.movies, tuple):
                raise TypeError("movies must be a tuple")
            query = LinkScreeningsQuery
            for screening in self.screenings:
                if not isinstance(screening, query.ScreeningInput):
                    raise TypeError("screenings must only contain ScreeningInput")
            for movie in self.movies:
                if not isinstance(movie, query.MovieInput):
                    raise TypeError("movies must only contain MovieInput")

    @dataclass(frozen=True, slots=True)
    class OutputData:
        movie_ids: tuple[str, ...]

    @dataclass(frozen=True, slots=True)
    class MovieKey:
        """What a screening and its movie have in common."""

        title: str
        source_identifier: str | None

    async def execute(self, input_data: InputData) -> OutputData:
        """Find the movie ID for every screening.

        Args:
            input_data: The screenings, and the stored movies they can belong to.

        Returns:
            One movie ID per screening, in the same order.

        Raises:
            MovieNotLinkedError: If a screening has no stored movie.
        """
        movie_ids = {
            self._build_key(movie.title, movie.source_identifier): movie.movie_id
            for movie in input_data.movies
        }
        logger.info("Linking %d screenings", len(input_data.screenings))
        return self.OutputData(
            movie_ids=tuple(
                self._find_movie_id(
                    movie_ids, screening.movie_title, screening.source_identifier
                )
                for screening in input_data.screenings
            )
        )

    def _build_key(self, title: str, source_identifier: str | None) -> MovieKey:
        """Build the key a screening and its movie share."""
        normalized_title = " ".join(title.strip().split()).lower()
        return self.MovieKey(normalized_title, source_identifier)

    def _find_movie_id(
        self,
        movie_ids: dict[MovieKey, str],
        title: str,
        source_identifier: str | None,
    ) -> str:
        """Return the movie ID for a screening, raising when none matches."""
        key = self._build_key(title, source_identifier)
        if key not in movie_ids:
            raise MovieNotLinkedError(f"No stored movie for screening of '{title}'")
        return movie_ids[key]
