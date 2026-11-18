"""Provider-independent metadata facts and retrieval capabilities.

Tuple order is provider order, including across internally retrieved pages.
Incomplete batches are never evidence of exhaustive absence. Failures are data,
not empty successful searches. Selection and locale policy belong to use cases.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

from marquise.application.exceptions.metadata_failure import MetadataFailure

type MatchReason = str
"""Stable name for why a movie has no identity, comparable across runs.

It is uncertain, no_match, or the failure class name, such as
MetadataNotFoundError or MetadataDetailMappingError.
"""


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    """An opaque movie or person ID scoped to its provider."""

    provider: str
    id: str

    def __post_init__(self) -> None:
        """Reject identities whose scope or identifier is missing."""
        if not self.provider.strip() or not self.id.strip():
            raise ValueError("Provider and ID must be nonempty")


@dataclass(frozen=True, slots=True)
class PersonFact:
    """Canonical person spelling and verified aliases for that person ID."""

    identity: ProviderIdentity
    name: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TitleFact:
    """Verified canonical, original, alternative or translation title."""

    title: str
    kind: Literal["canonical", "original", "alternative", "translation"]
    locale: str | None = None


@dataclass(frozen=True, slots=True)
class LocalizedMovieMetadata:
    """Unselected text/image values for one provider locale."""

    locale: str
    title: str | None = None
    synopsis: str | None = None
    poster_url: str | None = None


@dataclass(frozen=True, slots=True)
class MovieMedia:
    """Unselected media facts in provider order, with a resolved URL."""

    url: str
    language: str | None
    kind: Literal["trailer", "teaser", "other"]
    official: bool


@dataclass(frozen=True, slots=True)
class MovieCertification:
    """A provider certification with its country, without selection policy."""

    country: str
    rating: str


@dataclass(frozen=True, slots=True)
class MetadataMovie:
    """Identity evidence and optional enrichment facts, never a selected match."""

    identity: ProviderIdentity
    titles: tuple[TitleFact, ...]
    release_year: int | None = None
    duration_minutes: int | None = None
    directors: tuple[PersonFact, ...] = ()
    cast: tuple[PersonFact, ...] = ()
    original_title: str | None = None
    localized: tuple[LocalizedMovieMetadata, ...] = ()
    genres: tuple[str, ...] = ()
    origin_countries: tuple[str, ...] = ()
    media: tuple[MovieMedia, ...] = ()
    certifications: tuple[MovieCertification, ...] = ()
    tmdb_rating: float | None = None
    tmdb_vote_count: int | None = None


@dataclass(frozen=True, slots=True)
class MetadataBatch[FactT]:
    """Ordered facts; partial retrieval may carry useful items and a failure."""

    items: tuple[FactT, ...] = ()
    complete: bool = True
    failure: MetadataFailure | None = None

    def __post_init__(self) -> None:
        """A failed retrieval cannot claim completeness."""
        if self.failure is not None and self.complete:
            raise ValueError("Failed retrieval must be incomplete")


class MetadataRepository(ABC):
    """Injected discovery/detail port, with provider pagination hidden inside."""

    @abstractmethod
    async def search_movies(
        self, title: str, year: int | None = None
    ) -> MetadataBatch[MetadataMovie]:
        """Retrieve ordered title candidates without choosing an identity."""
        ...

    @abstractmethod
    async def search_people(self, name: str) -> MetadataBatch[PersonFact]:
        """Retrieve people with verified aliases, without spelling policy."""
        ...

    @abstractmethod
    async def directed_movies(
        self, person: ProviderIdentity
    ) -> MetadataBatch[MetadataMovie]:
        """Retrieve directed-film credits in provider order."""
        ...

    @abstractmethod
    async def movie_details(
        self, identity: ProviderIdentity
    ) -> MetadataBatch[MetadataMovie]:
        """Return zero or one movie; missing detail is a MetadataNotFoundError."""
        ...
