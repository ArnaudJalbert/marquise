"""Tests for domain movie exceptions."""

from __future__ import annotations

import pytest

from marquise.domain.exceptions import DomainError, MovieError
from marquise.domain.exceptions.movie import MovieNotFoundError


def test_movie_error_is_domain_error_subclass() -> None:
    """Verify MovieError inherits from DomainError."""
    assert issubclass(MovieError, DomainError)


def test_movie_not_found_error_is_movie_error_subclass() -> None:
    """Verify MovieNotFoundError inherits from MovieError."""
    assert issubclass(MovieNotFoundError, MovieError)


def test_movie_error_can_be_raised_and_caught() -> None:
    """Verify MovieError can be raised and caught."""
    with pytest.raises(MovieError):
        raise MovieError("test")


def test_movie_not_found_error_can_be_raised_and_caught() -> None:
    """Verify MovieNotFoundError can be raised and caught."""
    with pytest.raises(MovieNotFoundError):
        raise MovieNotFoundError("not found")


def test_movie_not_found_error_preserves_message() -> None:
    """Verify MovieNotFoundError preserves the provided message."""
    with pytest.raises(MovieNotFoundError, match="not found"):
        raise MovieNotFoundError("not found")
