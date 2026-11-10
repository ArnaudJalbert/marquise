"""Application exception re-exports."""

from marquise.application.exceptions.base import ApplicationError
from marquise.application.exceptions.cinema import (
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CinemaNotFoundError,
)
from marquise.application.exceptions.metadata_failure import (
    MetadataDetailMappingError,
    MetadataEndpointCheckError,
    MetadataFailure,
    MetadataInvalidDataError,
    MetadataMalformedJsonError,
    MetadataNotFoundError,
    MetadataPaginationError,
    MetadataRateLimitedError,
    MetadataRequestRefusedError,
    MetadataUnavailableError,
)
from marquise.application.exceptions.movie import (
    MovieIdentityConflictError,
    MovieMetadataUnavailableError,
    MovieNotFoundError,
    MovieNotLinkedError,
    MovieWorkflowConflictError,
    TooManyMovieIdsError,
)
from marquise.application.exceptions.screening import (
    ScreeningAlreadyExistsError,
    ScreeningExternalIdConflictError,
    ScreeningNotFoundError,
    ScreeningUpdateNotFoundError,
    TooManyScreeningDaysError,
)
from marquise.application.exceptions.source import (
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    SourceAlreadyExistsError,
    SourceNotFoundError,
)

__all__ = [
    "ApplicationError",
    "CinemaAlreadyExistsError",
    "CinemaIdAlreadyExistsError",
    "CinemaNotFoundError",
    "CinemaSourceAssignmentAlreadyExistsError",
    "CinemaSourceAssignmentNotFoundError",
    "MetadataDetailMappingError",
    "MetadataEndpointCheckError",
    "MetadataFailure",
    "MetadataInvalidDataError",
    "MetadataMalformedJsonError",
    "MetadataNotFoundError",
    "MetadataPaginationError",
    "MetadataRateLimitedError",
    "MetadataRequestRefusedError",
    "MetadataUnavailableError",
    "MovieIdentityConflictError",
    "MovieMetadataUnavailableError",
    "MovieNotFoundError",
    "MovieNotLinkedError",
    "MovieWorkflowConflictError",
    "ScreeningAlreadyExistsError",
    "ScreeningExternalIdConflictError",
    "ScreeningNotFoundError",
    "ScreeningUpdateNotFoundError",
    "SourceAlreadyExistsError",
    "SourceNotFoundError",
    "TooManyMovieIdsError",
    "TooManyScreeningDaysError",
]
