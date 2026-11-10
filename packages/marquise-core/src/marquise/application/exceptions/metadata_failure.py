"""Metadata retrieval failures, one class per way callers must treat them."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Literal

from marquise.application.exceptions.base import ApplicationError

if TYPE_CHECKING:
    from marquise.application.metadata import ProviderIdentity

type MetadataFailureReason = Literal[
    "pagination", "malformed_json", "endpoint_check", "detail_mapping"
]
"""Stable name of the provider check that rejected a response."""


# The established public name of the batch failure; subclasses carry Error.
@dataclass(frozen=True, slots=True)
class MetadataFailure(ApplicationError):  # noqa: N818
    """Retrieval failure, distinct from an exhaustive empty result.

    Use a subclass. Its type tells callers how to treat the failure.

    Attributes:
        code: Stable label of the subclass, safe to show in diagnostics.
        message: Sanitized diagnostic text, free of credentials, URLs and bodies.
        retryable: Whether repeating the request may succeed.
        reason: The failed check when a provider response was rejected.
        identity: The provider record involved, when one is known.
    """

    code: ClassVar[str]
    message: str
    retryable: bool = False
    reason: MetadataFailureReason | None = None
    identity: ProviderIdentity | None = None


class MetadataUnavailableError(MetadataFailure):
    """The provider or a collaborator could not answer."""

    code = "unavailable"


class MetadataRateLimitedError(MetadataFailure):
    """The provider refused the request until later."""

    code = "rate_limited"


class MetadataNotFoundError(MetadataFailure):
    """The requested record does not exist."""

    code = "not_found"


class MetadataInvalidDataError(MetadataFailure):
    """A response or record failed a check and cannot be trusted."""

    code = "invalid_data"
