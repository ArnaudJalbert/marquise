"""Tests for application-layer exceptions."""

from __future__ import annotations

import pytest

from marquise.application.exceptions import ApplicationError, CinemaIdAlreadyExistsError


def test_application_error_is_exception_subclass() -> None:
    assert issubclass(ApplicationError, Exception)


def test_cinema_id_already_exists_error_is_application_error_subclass() -> None:
    assert issubclass(CinemaIdAlreadyExistsError, ApplicationError)


def test_cinema_id_already_exists_error_can_be_raised_and_caught() -> None:
    with pytest.raises(CinemaIdAlreadyExistsError):
        raise CinemaIdAlreadyExistsError("test error")


def test_cinema_id_already_exists_error_preserves_message() -> None:
    with pytest.raises(CinemaIdAlreadyExistsError, match="test error"):
        raise CinemaIdAlreadyExistsError("test error")
