"""Tests for UpdateCinemaUseCase InputData/OutputData."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.update_cinema import UpdateCinemaUseCase


def test_input_data_rejects_empty_cinema_id() -> None:
    """Verify InputData rejects an empty cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        UpdateCinemaUseCase.InputData(cinema_id="", name="Test Cinema")


def test_input_data_rejects_whitespace_cinema_id() -> None:
    """Verify InputData rejects a whitespace-only cinema_id."""
    with pytest.raises(ValueError, match="cinema_id must not be empty"):
        UpdateCinemaUseCase.InputData(cinema_id="   ", name="Test Cinema")


def test_input_data_rejects_empty_name() -> None:
    """Verify InputData rejects an empty cinema name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        UpdateCinemaUseCase.InputData(cinema_id="cin-001", name="")


def test_input_data_rejects_whitespace_name() -> None:
    """Verify InputData rejects a whitespace-only name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        UpdateCinemaUseCase.InputData(cinema_id="cin-001", name="   ")


def test_input_data_rejects_empty_address_when_provided() -> None:
    """Verify InputData rejects an empty address string."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        UpdateCinemaUseCase.InputData(
            cinema_id="cin-001", name="Test Cinema", address=""
        )


def test_input_data_rejects_whitespace_address_when_provided() -> None:
    """Verify InputData rejects a whitespace-only address."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        UpdateCinemaUseCase.InputData(
            cinema_id="cin-001", name="Test Cinema", address="   "
        )


def test_input_data_rejects_empty_city_when_provided() -> None:
    """Verify InputData rejects an empty city string."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        UpdateCinemaUseCase.InputData(
            cinema_id="cin-001", name="Test Cinema", address="123 St", city=""
        )


def test_input_data_rejects_whitespace_city_when_provided() -> None:
    """Verify InputData rejects a whitespace-only city."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        UpdateCinemaUseCase.InputData(
            cinema_id="cin-001", name="Test Cinema", address="123 St", city="   "
        )


def test_input_data_rejects_empty_website_when_provided() -> None:
    """Verify InputData rejects an empty website string."""
    with pytest.raises(ValueError, match="website must not be empty when provided"):
        UpdateCinemaUseCase.InputData(
            cinema_id="cin-001", name="Test Cinema", website=""
        )


def test_input_data_rejects_whitespace_website_when_provided() -> None:
    """Verify InputData rejects a whitespace-only website."""
    with pytest.raises(ValueError, match="website must not be empty when provided"):
        UpdateCinemaUseCase.InputData(
            cinema_id="cin-001", name="Test Cinema", website="   "
        )


def test_input_data_allows_none_optionals() -> None:
    """Verify InputData allows None for optional fields."""
    data = UpdateCinemaUseCase.InputData(cinema_id="cin-001", name="Test Cinema")
    assert data.address is None
    assert data.city is None
    assert data.website is None


def test_input_data_allows_valid_input() -> None:
    """Verify InputData accepts valid data."""
    data = UpdateCinemaUseCase.InputData(
        cinema_id="cin-001",
        name="Test Cinema",
        address="123 St",
        city="Montreal",
        website="https://example.com",
    )
    assert data.cinema_id == "cin-001"
    assert data.name == "Test Cinema"
    assert data.address == "123 St"
    assert data.city == "Montreal"
    assert data.website == "https://example.com"


def test_output_data_creation() -> None:
    """Verify OutputData can be created with expected fields."""
    response = UpdateCinemaUseCase.OutputData(
        id="cin-001",
        name="Test Cinema",
        address="123 St",
        city="Montreal",
        website="https://example.com",
    )
    assert response.id == "cin-001"
    assert response.name == "Test Cinema"
    assert response.address == "123 St"
    assert response.city == "Montreal"
    assert response.website == "https://example.com"


def test_output_data_allows_none_optionals() -> None:
    """Verify OutputData allows None for optional fields."""
    data = UpdateCinemaUseCase.OutputData(id="cin-001", name="Test Cinema")
    assert data.address is None
    assert data.city is None
    assert data.website is None
