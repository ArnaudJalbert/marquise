"""Tests for source application exceptions."""

from __future__ import annotations

import pytest

from marquise.application.exceptions import (
    ApplicationError,
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    SourceAlreadyExistsError,
    SourceNotFoundError,
)


def test_source_already_exists_error_is_application_error_subclass() -> None:
    """Verify SourceAlreadyExistsError inherits from ApplicationError."""
    assert issubclass(SourceAlreadyExistsError, ApplicationError)


def test_source_not_found_error_is_application_error_subclass() -> None:
    """Verify SourceNotFoundError inherits from ApplicationError."""
    assert issubclass(SourceNotFoundError, ApplicationError)


def test_assignment_already_exists_is_app_error_subclass() -> None:
    """Verify CinemaSourceAssignmentAlreadyExistsError is an ApplicationError."""
    assert issubclass(CinemaSourceAssignmentAlreadyExistsError, ApplicationError)


def test_assignment_not_found_is_app_error_subclass() -> None:
    """Verify CinemaSourceAssignmentNotFoundError is an ApplicationError."""
    assert issubclass(CinemaSourceAssignmentNotFoundError, ApplicationError)


def test_source_already_exists_error_can_be_raised_and_caught() -> None:
    """Verify the exception can be raised and caught."""
    with pytest.raises(SourceAlreadyExistsError):
        raise SourceAlreadyExistsError("already exists")


def test_source_not_found_error_can_be_raised_and_caught() -> None:
    """Verify the exception can be raised and caught."""
    with pytest.raises(SourceNotFoundError):
        raise SourceNotFoundError("not found")


def test_source_already_exists_error_preserves_message() -> None:
    """Verify the exception preserves the provided message."""
    with pytest.raises(SourceAlreadyExistsError, match="already exists"):
        raise SourceAlreadyExistsError("already exists")


def test_source_not_found_error_preserves_message() -> None:
    """Verify the exception preserves the provided message."""
    with pytest.raises(SourceNotFoundError, match="not found"):
        raise SourceNotFoundError("not found")
