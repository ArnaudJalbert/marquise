"""Tests for ListCinemasUseCase InputData and CinemaData validation."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.list_cinemas import ListCinemasUseCase


def test_input_data_rejects_empty_name() -> None:
    """Verify InputData rejects an empty name string."""
    with pytest.raises(ValueError, match="name must not be empty when provided"):
        ListCinemasUseCase.InputData(name="")


def test_input_data_rejects_whitespace_name() -> None:
    """Verify InputData rejects a whitespace-only name."""
    with pytest.raises(ValueError, match="name must not be empty when provided"):
        ListCinemasUseCase.InputData(name="   ")


def test_cinema_data_allows_none_optional_fields() -> None:
    """Verify CinemaData allows None for optional fields."""
    data = ListCinemasUseCase.CinemaData(id="id-1", name="Test Cinema")
    assert data.address is None
    assert data.city is None
    assert data.website is None


def test_cinema_data_rejects_empty_id() -> None:
    """Verify CinemaData rejects an empty id."""
    with pytest.raises(ValueError, match="id must not be empty"):
        ListCinemasUseCase.CinemaData(id="", name="Test Cinema")


def test_cinema_data_rejects_whitespace_id() -> None:
    """Verify CinemaData rejects a whitespace-only id."""
    with pytest.raises(ValueError, match="id must not be empty"):
        ListCinemasUseCase.CinemaData(id="   ", name="Test Cinema")


def test_cinema_data_rejects_empty_name() -> None:
    """Verify CinemaData rejects an empty name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        ListCinemasUseCase.CinemaData(id="id-1", name="")


def test_cinema_data_rejects_whitespace_name() -> None:
    """Verify CinemaData rejects a whitespace-only name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        ListCinemasUseCase.CinemaData(id="id-1", name="   ")


def test_cinema_data_rejects_empty_address_when_provided() -> None:
    """Verify CinemaData rejects an empty address string."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        ListCinemasUseCase.CinemaData(id="id-1", name="Test", address="")


def test_cinema_data_rejects_whitespace_address_when_provided() -> None:
    """Verify CinemaData rejects a whitespace-only address."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        ListCinemasUseCase.CinemaData(id="id-1", name="Test", address="   ")


def test_cinema_data_rejects_empty_city_when_provided() -> None:
    """Verify CinemaData rejects an empty city string."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        ListCinemasUseCase.CinemaData(id="id-1", name="Test", address="123 St", city="")


def test_cinema_data_rejects_whitespace_city_when_provided() -> None:
    """Verify CinemaData rejects a whitespace-only city."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        ListCinemasUseCase.CinemaData(
            id="id-1", name="Test", address="123 St", city="   "
        )


def test_cinema_data_rejects_empty_website_when_provided() -> None:
    """Verify CinemaData rejects an empty website string."""
    with pytest.raises(ValueError, match="website must not be empty when provided"):
        ListCinemasUseCase.CinemaData(id="id-1", name="Test", website="")


def test_cinema_data_rejects_whitespace_website_when_provided() -> None:
    """Verify CinemaData rejects a whitespace-only website."""
    with pytest.raises(ValueError, match="website must not be empty when provided"):
        ListCinemasUseCase.CinemaData(id="id-1", name="Test", website="   ")


def test_output_data_rejects_negative_total() -> None:
    """Verify OutputData rejects a negative total."""
    with pytest.raises(ValueError, match="total must not be negative"):
        ListCinemasUseCase.OutputData(cinemas=[], total=-1)
