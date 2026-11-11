"""Shared workflow DTOs and stable-ID persistence contracts.

These contracts have no production implementations. IDs at delivery boundaries
are strings. tmdb_id is explicitly TMDB-only; another provider's identity must
never be assigned to it. A known identity does not imply successful enrichment.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from marquise.application.exceptions import (
    MetadataRateLimitedError,
    MetadataUnavailableError,
)
from marquise.application.exceptions import (
    MovieWorkflowConflictError as MovieWorkflowConflictError,
)
from marquise.application.metadata import ProviderIdentity


@dataclass(frozen=True, slots=True, kw_only=True)
class MovieMetadataValues:
    """Selected usable fields; None means preserve the stored/source value."""

    title: str | None = None
    original_title: str | None = None
    description: str | None = None
    release_year: int | None = None
    directors: tuple[str, ...] | None = None
    cast: tuple[str, ...] | None = None
    duration_minutes: int | None = None
    genres: tuple[str, ...] | None = None
    origin_countries: tuple[str, ...] | None = None
    poster_url: str | None = None
    trailer_url: str | None = None
    rating: str | None = None
    tmdb_rating: float | None = None
    tmdb_vote_count: int | None = None


@dataclass(frozen=True, slots=True)
class MovieMetadataSnapshot:
    """Stable movie state for enrichment and guarded merges.

    revision is opaque and changes for every metadata/reference change.
    Persistence must also recheck references and collisions atomically at merge.
    """

    movie_id: str
    revision: str
    values: MovieMetadataValues
    tmdb_id: str | None = None
    metadata_enriched_at: datetime | None = None
    screening_ids: tuple[str, ...] = ()
    unresolved_references: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EnrichMovieInputData:
    """Enrich a stable movie after confirmation, or explicitly refresh it."""

    movie_id: str
    identity: ProviderIdentity

    def __post_init__(self) -> None:
        """Require a stable movie identifier."""
        if not self.movie_id.strip():
            raise ValueError("Movie ID must not be blank")


@dataclass(frozen=True, slots=True)
class EnrichMovieOutputData:
    """A movie left not enriched keeps its fields and last successful enrichment.

    Attributes:
        failure: Why the movie was not enriched: a metadata failure or an
            internal error.
    """

    movie_id: str
    status: Literal["enriched", "unchanged", "not_enriched"]
    failure: Exception | None = None

    def __post_init__(self) -> None:
        """Only a movie left not enriched carries a failure."""
        if (self.status == "not_enriched") != (self.failure is not None):
            raise ValueError("Only not enriched results carry a failure")

    @property
    def retryable(self) -> bool:
        """Whether refreshing again later may succeed: an outage or rate limit."""
        return isinstance(
            self.failure, (MetadataUnavailableError, MetadataRateLimitedError)
        )


@dataclass(frozen=True, slots=True)
class RefreshMoviesInputData:
    """None selects all confirmed TMDB movies; a string selects exactly one."""

    movie_id: str | None = None

    def __post_init__(self) -> None:
        """Accept all movies or a nonblank movie identifier."""
        if self.movie_id is not None and not self.movie_id.strip():
            raise ValueError("Movie ID must not be blank")


@dataclass(frozen=True, slots=True)
class RefreshMoviesOutputData:
    """Per-movie outcomes in stable movie-ID order, without hiding failures."""

    results: tuple[EnrichMovieOutputData, ...]


@dataclass(frozen=True, slots=True)
class MergeMoviesInputData:
    """Targeted merge proposal. Apply requires the exact approved snapshot."""

    survivor_id: str
    duplicate_ids: tuple[str, ...]
    approved_snapshot: tuple[MovieMetadataSnapshot, ...] | None = None
    approved_identity: ProviderIdentity | None = None

    def __post_init__(self) -> None:
        """Require distinct nonempty targets; absence of approval means dry run."""
        ids = (self.survivor_id, *self.duplicate_ids)
        if not self.duplicate_ids or any(not value.strip() for value in ids):
            raise ValueError("Merge requires a survivor and duplicates")
        if len(set(ids)) != len(ids):
            raise ValueError("Merge IDs must be distinct")
        if self.approved_snapshot is not None and {
            item.movie_id for item in self.approved_snapshot
        } != set(ids):
            raise ValueError("Approval must cover exactly the targeted movies")


@dataclass(frozen=True, slots=True)
class MergeMoviesOutputData:
    """Dry-run snapshots or atomic applied result; blocked merges change nothing."""

    status: Literal["preview", "applied", "blocked"]
    snapshots: tuple[MovieMetadataSnapshot, ...]
    moved_screening_ids: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    confirmed_identity: ProviderIdentity | None = None


class MovieMetadataRepository(ABC):
    """Separate additive persistence port; existing repositories stay concrete."""

    @abstractmethod
    async def get(self, movie_id: str) -> MovieMetadataSnapshot | None:
        """Read a stable-ID snapshot, or None when missing."""
        ...

    @abstractmethod
    async def find_by_tmdb_id(self, tmdb_id: str) -> MovieMetadataSnapshot | None:
        """Read the explicitly TMDB-linked movie, without generic ID storage."""
        ...

    @abstractmethod
    async def list_tmdb_movies(self) -> tuple[MovieMetadataSnapshot, ...]:
        """Return confirmed TMDB movies in stable movie-ID order."""
        ...

    @abstractmethod
    async def update_metadata(
        self,
        expected: MovieMetadataSnapshot,
        values: MovieMetadataValues,
        tmdb_id: str,
        enriched_at: datetime,
    ) -> MovieMetadataSnapshot:
        """Atomically patch usable fields and stamp successful enrichment.

        Keep movie/screening IDs and source screening fields unchanged. Reject
        stale revision or conflicting TMDB identity with MovieWorkflowConflictError.
        Never stamp failures, and never clear fields for None patch values.
        """
        ...

    @abstractmethod
    async def merge(self, request: MergeMoviesInputData) -> MergeMoviesOutputData:
        """Preview without writes, or atomically apply the approved snapshot.

        Recheck all snapshots, collisions and unresolved references. Keep an
        existing TMDB-linked survivor. Move screenings preserving IDs; delete
        duplicates only after all references are moved. Blocked/stale requests
        change nothing and return blocked with reasons, including missing IDs.
        """
        ...
