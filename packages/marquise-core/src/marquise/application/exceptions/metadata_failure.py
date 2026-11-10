"""Metadata retrieval failures, one class per way a retrieval can fail."""

from __future__ import annotations

from marquise.application.exceptions.base import ApplicationError


# The established public name of the batch failure; subclasses carry Error.
class MetadataFailure(ApplicationError):  # noqa: N818
    """Retrieval failure, distinct from an exhaustive empty result.

    Use a subclass. Its type tells callers what failed. Its message is
    sanitized text, free of credentials, URLs and bodies.
    """


class MetadataUnavailableError(MetadataFailure):
    """The provider or a collaborator could not answer for now."""


class MetadataRequestRefusedError(MetadataFailure):
    """The provider refused the request, or it could not be sent at all."""


class MetadataRateLimitedError(MetadataFailure):
    """The provider refused the request until later."""


class MetadataNotFoundError(MetadataFailure):
    """The requested record does not exist."""


class MetadataInvalidDataError(MetadataFailure):
    """A response or record failed a check and cannot be trusted."""


class MetadataPaginationError(MetadataInvalidDataError):
    """Search pages disagreed with each other or with their totals."""


class MetadataMalformedJsonError(MetadataInvalidDataError):
    """A response was not a JSON object the provider documents."""


class MetadataEndpointCheckError(MetadataInvalidDataError):
    """A request path failed the allowed endpoint check before sending."""


class MetadataDetailMappingError(MetadataInvalidDataError):
    """A movie or person record could not be mapped to metadata facts."""
