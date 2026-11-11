"""Tests for application-layer exceptions."""

from __future__ import annotations

import pytest

from marquise import MovieWorkflowConflictError as PublicMovieWorkflowConflictError
from marquise.application.exceptions import (
    ApplicationError,
    MovieWorkflowConflictError,
)
from marquise.application.exceptions.movie import (
    MovieWorkflowConflictError as DefinedMovieWorkflowConflictError,
)
from marquise.application.movie_workflows import (
    MovieWorkflowConflictError as LegacyMovieWorkflowConflictError,
)


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
