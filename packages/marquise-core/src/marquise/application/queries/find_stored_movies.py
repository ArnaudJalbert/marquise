"""Query: find which source movies already have a stored movie."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from marquise.application.exceptions.movie import MovieIdentityConflictError
from marquise.application.metadata import ProviderIdentity
from marquise.application.repositories import MovieRepository
from marquise.domain.entities import Movie

logger = logging.getLogger(__name__)


class FindStoredMoviesQuery:
    """Sort source movies into stored and missing, without writing anything.

    A movie is found by its TMDB identity first, then by its titles. Each
    missing movie gets a key, so one film is only created once.
    """

    @dataclass(frozen=True, slots=True)
    class MovieInput:
        title: str
        source_identifier: str | None = None
        release_year: int | None = None
        matched_release_year: int | None = None
        identity: ProviderIdentity | None = None
        matched_titles: tuple[str, ...] = ()

        def __post_init__(self) -> None:
            if not isinstance(self.title, str):
                raise TypeError("title must be a string")
            if not isinstance(self.matched_titles, tuple):
                raise TypeError("matched_titles must be a tuple")
            self._check_optional(str, "source_identifier")
            self._check_optional(int, "release_year", "matched_release_year")
            self._check_optional(ProviderIdentity, "identity")

        def _check_optional(self, expected_type: type, *fields: str) -> None:
            for field in fields:
                value = getattr(self, field)
                if value is not None and not isinstance(value, expected_type):
                    raise TypeError(f"{field} must be a {expected_type.__name__}")

    @dataclass(frozen=True, slots=True)
    class InputData:
        movies: tuple[FindStoredMoviesQuery.MovieInput, ...]

        def __post_init__(self) -> None:
            if not isinstance(self.movies, tuple):
                raise TypeError("movies must be a tuple")
            for movie in self.movies:
                if not isinstance(movie, FindStoredMoviesQuery.MovieInput):
                    raise TypeError("movies must only contain MovieInput")

    @dataclass(frozen=True, slots=True)
    class StoredMovie:
        title: str
        source_identifier: str | None
        movie_id: str
        tmdb_id: str | None

    @dataclass(frozen=True, slots=True)
    class MissingMovie:
        title: str
        source_identifier: str | None
        saved_title: str
        release_year: int | None
        tmdb_id: str | None
        key: str

    @dataclass(frozen=True, slots=True)
    class OutputData:
        stored: tuple[FindStoredMoviesQuery.StoredMovie, ...]
        missing: tuple[FindStoredMoviesQuery.MissingMovie, ...]

    @dataclass(frozen=True, slots=True)
    class MatchedMovie:
        """A source movie with a TMDB identity and no linked stored movie yet."""

        source: FindStoredMoviesQuery.MovieInput
        tmdb_id: str
        release_year: int | None

    @dataclass(frozen=True, slots=True)
    class Identities:
        """Every source movie, sorted by what its identity already tells us."""

        stored: tuple[FindStoredMoviesQuery.StoredMovie, ...]
        matched: tuple[FindStoredMoviesQuery.MatchedMovie, ...]
        unmatched: tuple[FindStoredMoviesQuery.MovieInput, ...]

    def __init__(self, movie_repository: MovieRepository) -> None:
        self._movie_repository = movie_repository

    async def execute(self, input_data: InputData) -> OutputData:
        """Sort source movies into stored and missing.

        Args:
            input_data: The source movies and what matching found for them.

        Returns:
            The movies already stored, and the ones still to create.

        Raises:
            MovieIdentityConflictError: If another film owns a title and the
                movie has no release year to tell the two apart.
        """
        identities = await self._sort_by_identity(input_data.movies)
        title_candidates = await self._find_by_title(identities)
        results = self._compare_with_stored(identities, title_candidates)
        output = self._build_output(identities, results)
        logger.info("Found %d stored movies", len(output.stored))
        logger.info("Found %d missing movies", len(output.missing))
        return output

    async def _sort_by_identity(self, movies: tuple[MovieInput, ...]) -> Identities:
        """Sort every source movie by what its identity already tells us."""
        outcomes = [await self._sort_one(movie) for movie in movies]
        return self.Identities(
            stored=self._keep_of_type(outcomes, self.StoredMovie),
            matched=self._keep_of_type(outcomes, self.MatchedMovie),
            unmatched=self._keep_of_type(outcomes, self.MovieInput),
        )

    async def _sort_one(
        self, movie: MovieInput
    ) -> StoredMovie | MatchedMovie | MovieInput:
        """Link a stored TMDB identity. No TMDB identity keeps the source movie."""
        identity = movie.identity
        if identity is None or identity.provider != "tmdb":
            return movie
        stored = await self._movie_repository.find_by_tmdb_id(identity.id)
        if stored is None:
            release_year = movie.release_year or movie.matched_release_year
            return self.MatchedMovie(movie, identity.id, release_year)
        return self._build_stored_movie(movie, stored, identity.id)

    @staticmethod
    def _keep_of_type(outcomes: list, expected_type: type) -> tuple:
        """Keep the outcomes of one type."""
        return tuple(
            outcome for outcome in outcomes if isinstance(outcome, expected_type)
        )

    def _build_stored_movie(
        self, source: MovieInput, movie: Movie, tmdb_id: str | None
    ) -> StoredMovie:
        """Tie a source movie to a stored one, keeping the source title."""
        return self.StoredMovie(
            source.title, source.source_identifier, movie.id.value, tmdb_id
        )

    async def _find_by_title(self, identities: Identities) -> list[Movie]:
        """Load stored movies that could share a title with a source movie."""
        terms = self._choose_search_terms(identities)
        return await self._movie_repository.find_by_titles(terms)

    @staticmethod
    def _choose_search_terms(identities: Identities) -> list[str]:
        """Choose broad database search terms, with and without accents.

        Stored titles may or may not carry accents, and the database search is
        accent-sensitive, so both spellings are searched.
        """
        titles = [
            *(movie.title for movie in identities.unmatched),
            *(
                title
                for movie in identities.matched
                for title in (movie.source.title, *movie.source.matched_titles)
            ),
        ]
        keys = [
            key
            for title in titles
            for key in (
                Movie.title_key(title),
                FindStoredMoviesQuery._keep_accents(title),
            )
            if key
        ]
        return list(dict.fromkeys(max(key.split(), key=len) for key in keys))

    @staticmethod
    def _keep_accents(title: str) -> str:
        """Build a title key that keeps accents, because the search keeps them."""
        folded = Movie.search_title(title).casefold()
        return " ".join(
            "".join(char if char.isalnum() else " " for char in folded).split()
        )

    def _compare_with_stored(
        self, identities: Identities, title_candidates: list[Movie]
    ) -> list[StoredMovie | MissingMovie]:
        """Decide whether each remaining source movie is stored or missing."""
        return [
            *(
                self._compare_matched(movie, title_candidates)
                for movie in identities.matched
            ),
            *self._compare_all_unmatched(identities, title_candidates),
        ]

    def _compare_all_unmatched(
        self, identities: Identities, title_candidates: list[Movie]
    ) -> list[StoredMovie | MissingMovie]:
        """Compare every unmatched movie, sharing the batch's matched identities."""
        aliases = self._map_titles_to_identities(identities.matched)
        return [
            self._compare_unmatched(movie, title_candidates, aliases)
            for movie in identities.unmatched
        ]

    @staticmethod
    def _map_titles_to_identities(matched: tuple[MatchedMovie, ...]) -> dict[str, str]:
        """Map title keys to the batch's single matched identity for that title.

        Label variants such as ``Fjord (VOSTA)`` then share the matched row
        instead of creating an unmatched twin in the same import.
        """
        owners: dict[str, set[str]] = {}
        for movie in matched:
            for title in (movie.source.title, *movie.source.matched_titles):
                owners.setdefault(Movie.title_key(title), set()).add(movie.tmdb_id)
        return {
            key: f"tmdb:{next(iter(ids))}"
            for key, ids in owners.items()
            if key and len(ids) == 1
        }

    def _compare_matched(
        self, matched: MatchedMovie, title_candidates: list[Movie]
    ) -> StoredMovie | MissingMovie:
        """Compare a matched movie with the rows its identity could own."""
        saved_title = self._choose_saved_title(matched, title_candidates)
        stored = self._find_stored_matched(matched, title_candidates)
        if stored is not None:
            return self._build_stored_movie(matched.source, stored, matched.tmdb_id)
        return self._build_missing_matched_movie(matched, saved_title)

    def _build_missing_matched_movie(
        self, matched: MatchedMovie, saved_title: str
    ) -> MissingMovie:
        """Describe a matched movie still to create, keyed by its identity."""
        return self.MissingMovie(
            title=matched.source.title,
            source_identifier=matched.source.source_identifier,
            saved_title=saved_title,
            release_year=matched.release_year,
            tmdb_id=matched.tmdb_id,
            key=f"tmdb:{matched.tmdb_id}",
        )

    def _choose_saved_title(
        self, matched: MatchedMovie, title_candidates: list[Movie]
    ) -> str:
        """Return the title to store. A remake takes its year to stay distinct."""
        title = self._normalize_title(matched.source.title)
        if not self._is_title_owned_by_another_film(matched, title_candidates):
            return title
        if matched.release_year is None:
            raise MovieIdentityConflictError(
                f"Movie '{title}' already has a different TMDB id"
            )
        return f"{title} ({matched.release_year})"

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Strip and collapse internal whitespace in a scraped movie title."""
        return " ".join(title.strip().split())

    @staticmethod
    def _is_title_owned_by_another_film(
        matched: MatchedMovie, title_candidates: list[Movie]
    ) -> bool:
        """Check whether a different known film already uses this title."""
        title = Movie.search_title(matched.source.title).casefold()
        return any(
            movie.tmdb_id not in {None, matched.tmdb_id}
            and Movie.search_title(movie.title).casefold() == title
            for movie in title_candidates
        )

    def _find_stored_matched(
        self, matched: MatchedMovie, title_candidates: list[Movie]
    ) -> Movie | None:
        """Find the row for a matched movie, ignoring rows owned by other films."""
        title = self._normalize_title(matched.source.title)
        titles = (title, *matched.source.matched_titles)
        candidates = [
            movie
            for movie in title_candidates
            if movie.tmdb_id in {None, matched.tmdb_id}
        ]
        return self._find_match(candidates, titles, matched.release_year)

    def _compare_unmatched(
        self, movie: MovieInput, title_candidates: list[Movie], aliases: dict[str, str]
    ) -> StoredMovie | MissingMovie:
        """Compare an unmatched movie with stored rows by title alone."""
        title = self._normalize_title(movie.title)
        stored = self._find_match(title_candidates, (title,), movie.release_year)
        if stored is not None:
            return self._build_stored_movie(movie, stored, None)
        return self._build_missing_unmatched_movie(movie, title, aliases)

    def _build_missing_unmatched_movie(
        self, movie: MovieInput, title: str, aliases: dict[str, str]
    ) -> MissingMovie:
        """Describe an unmatched movie still to create, keyed by its title."""
        key = Movie.title_key(movie.title)
        return self.MissingMovie(
            title=movie.title,
            source_identifier=movie.source_identifier,
            saved_title=title,
            release_year=movie.release_year,
            tmdb_id=None,
            key=aliases.get(key, f"title:{key}"),
        )

    def _find_match(
        self,
        candidates: list[Movie],
        titles: tuple[str, ...],
        release_year: int | None,
    ) -> Movie | None:
        """Return the one compatible candidate by title key, then containment.

        Comparison ignores case, accents, punctuation and screening labels.
        Ambiguous candidates return None so a new movie is created instead.
        """
        compatible_movies = self._keep_year_compatible(candidates, release_year)
        same_key = self._keep_same_title_key(compatible_movies, titles)
        if same_key:
            return self._get_only_movie(self._prefer_exact(same_key, titles))
        return self._get_only_movie(self._keep_overlapping(compatible_movies, titles))

    @staticmethod
    def _keep_year_compatible(
        candidates: list[Movie], release_year: int | None
    ) -> list[Movie]:
        """Keep candidates whose release year doesn't contradict the source."""
        return [
            movie
            for movie in candidates
            if release_year is None
            or movie.release_year is None
            or movie.release_year == release_year
        ]

    @staticmethod
    def _keep_same_title_key(
        candidates: list[Movie], titles: tuple[str, ...]
    ) -> list[Movie]:
        """Keep candidates whose canonical title equals one of the titles."""
        keys = {key for title in titles if (key := Movie.title_key(title))}
        return [movie for movie in candidates if Movie.title_key(movie.title) in keys]

    def _prefer_exact(
        self, candidates: list[Movie], titles: tuple[str, ...]
    ) -> list[Movie]:
        """Narrow to the single exact spelling, when there is exactly one."""
        wanted_titles = {self._normalize_title(title).casefold() for title in titles}
        exact_matches = [
            movie
            for movie in candidates
            if self._normalize_title(movie.title).casefold() in wanted_titles
        ]
        return exact_matches if len(exact_matches) == 1 else candidates

    @staticmethod
    def _keep_overlapping(
        candidates: list[Movie], titles: tuple[str, ...]
    ) -> list[Movie]:
        """Keep candidates whose title contains, or is contained by, a title."""
        return [
            movie
            for movie in candidates
            if any(Movie.titles_overlap(movie.title, title) for title in titles)
        ]

    @staticmethod
    def _get_only_movie(movies: list[Movie]) -> Movie | None:
        """Return the movie when there is exactly one."""
        return movies[0] if len(movies) == 1 else None

    def _build_output(
        self, identities: Identities, results: list[StoredMovie | MissingMovie]
    ) -> OutputData:
        """Combine movies linked by identity with the title comparison results."""
        return self.OutputData(
            stored=(*identities.stored, *self._keep_of_type(results, self.StoredMovie)),
            missing=self._keep_of_type(results, self.MissingMovie),
        )
