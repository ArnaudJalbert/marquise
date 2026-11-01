"""Movie entity representing a film."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime

from ..value_objects import MovieId

_LANGUAGE = (
    r"(?:fran[cç]ais(?:e)?|anglais(?:e)?|english|french|tamil|tamoul|punjabi|"
    r"pendjabi|espagnol(?:e)?|spanish|japanese|japonais(?:e)?|hindi|german|"
    r"allemand(?:e)?|korean|cor[ée]en(?:ne)?|italian|italien(?:ne)?|"
    r"multilingual|multilingue)"
)
_SUBTITLES = r"(?:w[/.]e\.s\.t\.?|(?:avec\s+)?s\.?t\.?f\.?|dubbed)"
# Screening labels that cinemas append to a film title. Only complete trailing
# labels are removed, never arbitrary parentheses or subtitles.
_LABEL = (
    rf"(?:version\s+{_LANGUAGE}|{_LANGUAGE}\s+{_SUBTITLES}|"
    r"[A-Z]{3}\.ENG\.SUB|VOSTF|VOSTA|VOA|VOF|VF|"
    r"\d+(?:e|er|th)?\s+anniversaire|derni[eè]re\s+s[ée]ance|"
    r"(?:an\s+)?imax(?:\s+3d)?(?:\s+experience)?|3d)"
)
_TRAILING_LABEL = re.compile(
    rf"(?:\s*[(\[]\s*(?:{_LABEL}|{_LANGUAGE})\s*[)\]]|\s*[:\-]\s*{_LABEL}|\s+{_LABEL})\s*$",
    re.IGNORECASE,
)


@dataclass(kw_only=True, slots=True)
class Movie:
    """A movie with its core details.

    Attributes:
        id: Unique identifier for the movie.
        title: Official title of the movie.
        release_year: Theatrical release year (None if unknown).
        directors: Tuple of director names (None if unknown).
        cast: Tuple of cast member names (None if unknown).
        duration_minutes: Runtime in minutes (optional).
        description: Plot synopsis (optional).
        poster_url: URL to the movie poster image (optional).
        trailer_url: URL to the movie trailer (optional).
        genres: Tuple of genre names (optional).
        original_title: Original title in native language (optional).
        rating: Content rating (e.g. ``"18+"``) (optional).
        origin_countries: Tuple of production country names (optional).
        tmdb_rating: TMDB user score out of ten (optional).
        tmdb_vote_count: Number of TMDB user votes (optional).
    """

    id: MovieId
    title: str
    release_year: int | None = None
    directors: tuple[str, ...] | None = None
    cast: tuple[str, ...] | None = None
    duration_minutes: int | None = None
    description: str | None = None
    poster_url: str | None = None
    trailer_url: str | None = None
    genres: tuple[str, ...] | None = None
    original_title: str | None = None
    rating: str | None = None
    origin_countries: tuple[str, ...] | None = None
    # Identity confirmation alone does not mean metadata enrichment succeeded.
    tmdb_id: str | None = None
    metadata_enriched_at: datetime | None = None
    tmdb_rating: float | None = None
    tmdb_vote_count: int | None = None

    def __post_init__(self) -> None:
        """Validate movie data after initialization.

        Raises:
            ValueError: If the title is empty, no directors are provided,
                a director name is empty, duration or release year is
                non-positive, or a TMDB score is out of range.
        """
        if not self.title.strip():
            raise ValueError("Movie title cannot be empty")
        if self.directors is not None:
            if not self.directors:
                raise ValueError("Movie must have at least one director")
            if not all(d.strip() for d in self.directors):
                raise ValueError("Director name cannot be empty")
        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValueError("Movie duration must be positive")
        if self.release_year is not None and self.release_year <= 0:
            raise ValueError("Movie release year must be positive")
        if self.tmdb_rating is not None and (
            isinstance(self.tmdb_rating, bool)
            or not isinstance(self.tmdb_rating, (int, float))
            or not 0 <= self.tmdb_rating <= 10
        ):
            raise ValueError("Movie TMDB rating must be between 0 and 10")
        if self.tmdb_vote_count is not None and (
            isinstance(self.tmdb_vote_count, bool)
            or not isinstance(self.tmdb_vote_count, int)
            or self.tmdb_vote_count < 0
        ):
            raise ValueError("Movie TMDB vote count must be a non-negative integer")

    @staticmethod
    def search_title(title: str) -> str:
        """Return the film title without trailing screening version labels."""
        title = " ".join(html.unescape(title).split())
        while (cleaned := _TRAILING_LABEL.sub("", title).strip()) != title:
            title = cleaned
        return title

    @classmethod
    def title_key(cls, title: str) -> str:
        """Return a canonical key for comparing movie title variants.

        Case, accents, punctuation, English articles and screening labels
        such as ``(VOSTF)`` or ``(Japanese w/e.s.t.)`` are ignored.
        """
        folded = "".join(
            char
            for char in unicodedata.normalize("NFKD", cls.search_title(title))
            if not unicodedata.combining(char)
        ).casefold()
        words = "".join(char if char.isalnum() else " " for char in folded).split()
        # English articles are dropped anywhere: "Beast of Mossy Bottom" and
        # "The Beast of Mossy Bottom" are one film. A title made only of
        # articles keeps its words.
        return " ".join(
            [word for word in words if word not in {"a", "an", "the"}] or words
        )

    @classmethod
    def titles_overlap(cls, left: str, right: str) -> bool:
        """Whether one title key equals or contains the other as whole words.

        The shorter key needs at least two words or six characters, so a
        generic one-word title never absorbs a longer, different film.
        """
        a, b = sorted((cls.title_key(left), cls.title_key(right)), key=len)
        if not a or (a.count(" ") == 0 and len(a) < 6):
            return False
        return a == b or f" {a} " in f" {b} "

    def is_recent(self, years: int = 1) -> bool:
        """Check if the movie was released within the last specified years.

        Args:
            years: Number of years to consider as "recent" (default 1).

        Returns:
            True if the movie's release year is within the given window,
            False if the release year is unknown.
        """
        if self.release_year is None:
            return False
        return datetime.now(UTC).year - self.release_year <= years
