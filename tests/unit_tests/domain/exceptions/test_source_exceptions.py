"""Tests for domain source exceptions."""

from __future__ import annotations

import pytest

from marquise.domain.exceptions import (
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    DomainError,
    SourceAlreadyExistsError,
    SourceError,
    SourceNotFoundError,
)


def test_source_error_is_domain_error_subclass() -> None:
    """Verify SourceError inherits from DomainError."""
    assert issubclass(SourceError, DomainError)


def test_source_not_found_error_is_source_error_subclass() -> None:
    """Verify SourceNotFoundError inherits from SourceError."""
    assert issubclass(SourceNotFoundError, SourceError)


def test_source_already_exists_error_is_source_error_subclass() -> None:
    """Verify SourceAlreadyExistsError inherits from SourceError."""
    assert issubclass(SourceAlreadyExistsError, SourceError)


def test_cinema_source_assignment_not_found_error_is_source_error_subclass() -> None:
    """Verify CinemaSourceAssignmentNotFoundError inherits from SourceError."""
    assert issubclass(CinemaSourceAssignmentNotFoundError, SourceError)


def test_cinema_source_assignment_already_exists_error_is_source_error_subclass() -> (
    None
):
    """Verify CinemaSourceAssignmentAlreadyExistsError inherits from SourceError."""
    assert issubclass(CinemaSourceAssignmentAlreadyExistsError, SourceError)


def test_source_error_can_be_raised_and_caught() -> None:
    """Verify SourceError can be raised and caught."""
    with pytest.raises(SourceError):
        raise SourceError("test")


def test_source_not_found_error_can_be_raised_and_caught() -> None:
    """Verify SourceNotFoundError can be raised and caught."""
    with pytest.raises(SourceNotFoundError):
        raise SourceNotFoundError("not found")


def test_source_already_exists_error_can_be_raised_and_caught() -> None:
    """Verify SourceAlreadyExistsError can be raised and caught."""
    with pytest.raises(SourceAlreadyExistsError):
        raise SourceAlreadyExistsError("already exists")


def test_source_not_found_error_preserves_message() -> None:
    """Verify SourceNotFoundError preserves the provided message."""
    with pytest.raises(SourceNotFoundError, match="not found"):
        raise SourceNotFoundError("not found")


def test_source_already_exists_error_preserves_message() -> None:
    """Verify SourceAlreadyExistsError preserves the provided message."""
    with pytest.raises(SourceAlreadyExistsError, match="already exists"):
        raise SourceAlreadyExistsError("already exists")
