"""Tests for domain screening exceptions."""

from __future__ import annotations

import pytest

from marquise.domain.exceptions import DomainError, ScreeningError
from marquise.domain.exceptions.screening import ScreeningNotFoundError


def test_screening_error_is_domain_error_subclass() -> None:
    """Verify ScreeningError inherits from DomainError."""
    assert issubclass(ScreeningError, DomainError)


def test_screening_not_found_error_is_screening_error_subclass() -> None:
    """Verify ScreeningNotFoundError inherits from ScreeningError."""
    assert issubclass(ScreeningNotFoundError, ScreeningError)


def test_screening_error_can_be_raised_and_caught() -> None:
    """Verify ScreeningError can be raised and caught."""
    with pytest.raises(ScreeningError):
        raise ScreeningError("test")


def test_screening_not_found_error_can_be_raised_and_caught() -> None:
    """Verify ScreeningNotFoundError can be raised and caught."""
    with pytest.raises(ScreeningNotFoundError):
        raise ScreeningNotFoundError("not found")


def test_screening_not_found_error_preserves_message() -> None:
    """Verify ScreeningNotFoundError preserves the provided message."""
    with pytest.raises(ScreeningNotFoundError, match="not found"):
        raise ScreeningNotFoundError("not found")
