"""Tests for application DTOs."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.create_cinema import CreateCinemaUseCase


def test_input_data_rejects_empty_name() -> None:
    """Verify InputData rejects an empty cinema name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateCinemaUseCase.InputData(name="", address="123 Test St", city="Montreal")


def test_input_data_rejects_whitespace_name() -> None:
    """Verify InputData rejects a whitespace-only name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateCinemaUseCase.InputData(
            name="   ", address="123 Test St", city="Montreal"
        )


def test_input_data_rejects_empty_address_when_provided() -> None:
    """Verify InputData rejects an empty address string."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        CreateCinemaUseCase.InputData(name="Test Cinema", address="")


def test_input_data_rejects_whitespace_address_when_provided() -> None:
    """Verify InputData rejects a whitespace-only address."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        CreateCinemaUseCase.InputData(name="Test Cinema", address="   ")


def test_input_data_rejects_empty_city_when_provided() -> None:
    """Verify InputData rejects an empty city string."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        CreateCinemaUseCase.InputData(
            name="Test Cinema", address="123 Test St", city=""
        )


def test_input_data_rejects_whitespace_city_when_provided() -> None:
    """Verify InputData rejects a whitespace-only city."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        CreateCinemaUseCase.InputData(
            name="Test Cinema", address="123 Test St", city="   "
        )


def test_input_data_allows_none_address_and_city() -> None:
    """Verify InputData allows None for optional fields."""
    data = CreateCinemaUseCase.InputData(name="Test Cinema")
    assert data.address is None
    assert data.city is None


def test_input_data_allows_valid_input() -> None:
    """Verify InputData accepts valid data."""
    data = CreateCinemaUseCase.InputData(
        name="Test Cinema", address="123 Test St", city="Montreal"
    )
    assert data.name == "Test Cinema"
    assert data.address == "123 Test St"
    assert data.city == "Montreal"


def test_output_data_creation() -> None:
    """Verify OutputData can be created with expected fields."""
    response = CreateCinemaUseCase.OutputData(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
    )
    assert response.id == "550e8400-e29b-41d4-a716-446655440000"
    assert response.name == "Test Cinema"
    assert response.address == "123 Test St"
    assert response.city == "Montreal"


def test_output_data_rejects_empty_id() -> None:
    """Verify OutputData rejects an empty id."""
    with pytest.raises(ValueError, match="id must not be empty"):
        CreateCinemaUseCase.OutputData(
            id="", name="Test Cinema", address="123 Test St", city="Montreal"
        )


def test_output_data_rejects_whitespace_id() -> None:
    """Verify OutputData rejects a whitespace-only id."""
    with pytest.raises(ValueError, match="id must not be empty"):
        CreateCinemaUseCase.OutputData(
            id="   ", name="Test Cinema", address="123 Test St", city="Montreal"
        )


def test_output_data_rejects_empty_name() -> None:
    """Verify OutputData rejects an empty name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateCinemaUseCase.OutputData(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="",
            address="123 Test St",
            city="Montreal",
        )


def test_output_data_rejects_empty_address_when_provided() -> None:
    """Verify OutputData rejects an empty address string."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        CreateCinemaUseCase.OutputData(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="Test Cinema",
            address="",
        )


def test_output_data_rejects_empty_city_when_provided() -> None:
    """Verify OutputData rejects an empty city string."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        CreateCinemaUseCase.OutputData(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="Test Cinema",
            address="123 Test St",
            city="",
        )


def test_output_data_allows_none_address_and_city() -> None:
    """Verify OutputData allows None for optional fields."""
    data = CreateCinemaUseCase.OutputData(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="Test Cinema",
    )
    assert data.address is None
    assert data.city is None
