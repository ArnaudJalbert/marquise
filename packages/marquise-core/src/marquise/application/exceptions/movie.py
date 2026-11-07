"""Movie-related application exceptions."""

from __future__ import annotations

from marquise.application.exceptions.base import ApplicationError


class MovieWorkflowConflictError(ApplicationError):
    """Stale state, identity conflict or unsafe references prevented a write."""


class MovieIdentityConflictError(ApplicationError):
    """A title is already assigned to a different known movie."""


class MovieMetadataUnavailableError(ApplicationError):
    """The metadata provider could not answer, so the work can't be trusted."""


class MovieNotFoundError(ApplicationError):
    """Raised when a requested movie does not exist in the repository."""

    pass


class TooManyMovieIdsError(ApplicationError):
    """Raised when a bulk movie lookup requests more IDs than allowed."""

    pass
