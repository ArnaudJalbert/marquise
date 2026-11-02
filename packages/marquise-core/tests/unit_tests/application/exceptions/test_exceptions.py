"""Tests for application-layer exceptions."""

from __future__ import annotations

import pytest

from marquise import MovieWorkflowConflictError as PublicMovieWorkflowConflictError
from marquise.application.exceptions import (
    ApplicationError,
    CinemaIdAlreadyExistsError,
    MovieWorkflowConflictError,
)
from marquise.application.exceptions.movie import (
    MovieWorkflowConflictError as DefinedMovieWorkflowConflictError,
)
from marquise.application.movie_workflows import (
    MovieWorkflowConflictError as LegacyMovieWorkflowConflictError,
)


def test_application_error_is_exception_subclass() -> None:
    """Verify ApplicationError inherits from Exception."""
    assert issubclass(ApplicationError, Exception)


def test_cinema_id_already_exists_error_is_application_error_subclass() -> None:
    """Verify CinemaIdAlreadyExistsError inherits from ApplicationError."""
    assert issubclass(CinemaIdAlreadyExistsError, ApplicationError)


def test_cinema_id_already_exists_error_can_be_raised_and_caught() -> None:
    """Verify the exception can be raised and caught."""
    with pytest.raises(CinemaIdAlreadyExistsError):
        raise CinemaIdAlreadyExistsError("test error")


def test_cinema_id_already_exists_error_preserves_message() -> None:
    """Verify the exception preserves the provided message."""
    with pytest.raises(CinemaIdAlreadyExistsError, match="test error"):
        raise CinemaIdAlreadyExistsError("test error")


def test_movie_workflow_conflict_error_preserves_legacy_contract() -> None:
    """All import paths share the moved application error and its message behavior."""
    assert MovieWorkflowConflictError is DefinedMovieWorkflowConflictError
    assert MovieWorkflowConflictError is LegacyMovieWorkflowConflictError
    assert MovieWorkflowConflictError is PublicMovieWorkflowConflictError
    assert (
        MovieWorkflowConflictError.__module__ == "marquise.application.exceptions.movie"
    )
    assert MovieWorkflowConflictError.__bases__ == (ApplicationError,)
    with pytest.raises(LegacyMovieWorkflowConflictError, match="stale state") as caught:
        raise MovieWorkflowConflictError("stale state")
    assert caught.value.args == ("stale state",)
