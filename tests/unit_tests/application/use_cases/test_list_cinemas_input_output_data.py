"""Tests for ListCinemasUseCase InputData and CinemaData validation."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.list_cinemas import ListCinemasUseCase


def test_input_data_defaults_to_none_name() -> None:
    """Verify InputData defaults name to None."""
    data = ListCinemasUseCase.InputData()
    assert data.name is None


def test_input_data_allows_valid_name() -> None:
    """Verify InputData accepts a valid name."""
    data = ListCinemasUseCase.InputData(name="Cinema")
    assert data.name == "Cinema"


def test_input_data_rejects_empty_name() -> None:
    """Verify InputData rejects an empty name string."""
    with pytest.raises(ValueError, match="name must not be empty when provided"):
        ListCinemasUseCase.InputData(name="")


def test_input_data_rejects_whitespace_name() -> None:
    """Verify InputData rejects a whitespace-only name."""
    with pytest.raises(ValueError, match="name must not be empty when provided"):
        ListCinemasUseCase.InputData(name="   ")


def test_cinema_data_creation() -> None:
    """Verify CinemaData can be created with all fields."""
    data = ListCinemasUseCase.CinemaData(
        id="id-1",
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )
    assert data.id == "id-1"
    assert data.name == "Test Cinema"
    assert data.address == "123 Test St"
    assert data.city == "Montreal"
    assert data.website == "https://example.com"


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


def test_output_data_creation() -> None:
    """Verify OutputData can be created with a list of CinemaData."""
    cinema = ListCinemasUseCase.CinemaData(id="id-1", name="Test Cinema")
    data = ListCinemasUseCase.OutputData(cinemas=[cinema], total=1)
    assert len(data.cinemas) == 1
    assert data.cinemas[0].id == "id-1"
    assert data.cinemas[0].name == "Test Cinema"
    assert data.total == 1


def test_output_data_empty_list() -> None:
    """Verify OutputData accepts an empty list."""
    data = ListCinemasUseCase.OutputData(cinemas=[], total=0)
    assert len(data.cinemas) == 0


def test_output_data_rejects_negative_total() -> None:
    """Verify OutputData rejects a negative total."""
    with pytest.raises(ValueError, match="total must not be negative"):
        ListCinemasUseCase.OutputData(cinemas=[], total=-1)


def test_input_data_rejects_page_below_one() -> None:
    """Verify InputData rejects a page less than 1."""
    with pytest.raises(ValueError, match="page must be at least 1"):
        ListCinemasUseCase.InputData(page=0)


def test_input_data_rejects_non_positive_size() -> None:
    """Verify InputData rejects a size less than 1 when provided."""
    with pytest.raises(ValueError, match="size must be positive when provided"):
        ListCinemasUseCase.InputData(size=0)


def test_input_data_allows_none_size() -> None:
    """Verify InputData allows size=None (unbounded)."""
    data = ListCinemasUseCase.InputData(size=None)
    assert data.size is None
