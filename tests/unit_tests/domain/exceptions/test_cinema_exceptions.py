"""Tests for domain cinema exceptions."""

from __future__ import annotations

import pytest

from marquise.domain.exceptions import CinemaError, DomainError
from marquise.domain.exceptions.cinema import (
    CinemaAlreadyExistsError,
    CinemaNotFoundError,
)


def test_cinema_error_is_domain_error_subclass() -> None:
    """Verify CinemaError inherits from DomainError."""
    assert issubclass(CinemaError, DomainError)


def test_cinema_not_found_error_is_cinema_error_subclass() -> None:
    """Verify CinemaNotFoundError inherits from CinemaError."""
    assert issubclass(CinemaNotFoundError, CinemaError)


def test_cinema_already_exists_error_is_cinema_error_subclass() -> None:
    """Verify CinemaAlreadyExistsError inherits from CinemaError."""
    assert issubclass(CinemaAlreadyExistsError, CinemaError)


def test_cinema_error_can_be_raised_and_caught() -> None:
    """Verify CinemaError can be raised and caught."""
    with pytest.raises(CinemaError):
        raise CinemaError("test")


def test_cinema_not_found_error_can_be_raised_and_caught() -> None:
    """Verify CinemaNotFoundError can be raised and caught."""
    with pytest.raises(CinemaNotFoundError):
        raise CinemaNotFoundError("not found")


def test_cinema_already_exists_error_can_be_raised_and_caught() -> None:
    """Verify CinemaAlreadyExistsError can be raised and caught."""
    with pytest.raises(CinemaAlreadyExistsError):
        raise CinemaAlreadyExistsError("already exists")


def test_cinema_not_found_error_preserves_message() -> None:
    """Verify CinemaNotFoundError preserves the provided message."""
    with pytest.raises(CinemaNotFoundError, match="not found"):
        raise CinemaNotFoundError("not found")


def test_cinema_already_exists_error_preserves_message() -> None:
    """Verify CinemaAlreadyExistsError preserves the provided message."""
    with pytest.raises(CinemaAlreadyExistsError, match="already exists"):
        raise CinemaAlreadyExistsError("already exists")
