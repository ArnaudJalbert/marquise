"""Tests for application DTOs."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.create_cinema import CreateCinemaUseCase


def test_input_data_rejects_empty_name() -> None:
    """Verify InputData rejects an empty cinema name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateCinemaUseCase.InputData(
            name="",
            address="123 Test St",
            city="Montreal",
            website="https://example.com",
        )


def test_input_data_rejects_whitespace_name() -> None:
    """Verify InputData rejects a whitespace-only name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateCinemaUseCase.InputData(
            name="   ",
            address="123 Test St",
            city="Montreal",
            website="https://example.com",
        )


def test_input_data_rejects_empty_address_when_provided() -> None:
    """Verify InputData rejects an empty address string."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        CreateCinemaUseCase.InputData(
            name="Test Cinema", address="", website="https://example.com"
        )


def test_input_data_rejects_whitespace_address_when_provided() -> None:
    """Verify InputData rejects a whitespace-only address."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        CreateCinemaUseCase.InputData(
            name="Test Cinema", address="   ", website="https://example.com"
        )


def test_input_data_rejects_empty_city_when_provided() -> None:
    """Verify InputData rejects an empty city string."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        CreateCinemaUseCase.InputData(
            name="Test Cinema",
            address="123 Test St",
            city="",
            website="https://example.com",
        )


def test_input_data_rejects_whitespace_city_when_provided() -> None:
    """Verify InputData rejects a whitespace-only city."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        CreateCinemaUseCase.InputData(
            name="Test Cinema",
            address="123 Test St",
            city="   ",
            website="https://example.com",
        )


def test_input_data_allows_none_address_and_city() -> None:
    """Verify InputData allows None for optional fields."""
    data = CreateCinemaUseCase.InputData(name="Test Cinema")
    assert data.address is None
    assert data.city is None
    assert data.website is None


def test_input_data_allows_valid_input() -> None:
    """Verify InputData accepts valid data."""
    data = CreateCinemaUseCase.InputData(
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )
    assert data.name == "Test Cinema"
    assert data.address == "123 Test St"
    assert data.city == "Montreal"
    assert data.website == "https://example.com"


def test_input_data_rejects_empty_website_when_provided() -> None:
    """Verify InputData rejects an empty website string."""
    with pytest.raises(ValueError, match="website must not be empty when provided"):
        CreateCinemaUseCase.InputData(name="Test Cinema", website="")


def test_input_data_rejects_whitespace_website_when_provided() -> None:
    """Verify InputData rejects a whitespace-only website."""
    with pytest.raises(ValueError, match="website must not be empty when provided"):
        CreateCinemaUseCase.InputData(name="Test Cinema", website="   ")


def test_output_data_creation() -> None:
    """Verify OutputData can be created with expected fields."""
    response = CreateCinemaUseCase.OutputData(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )
    assert response.id == "550e8400-e29b-41d4-a716-446655440000"
    assert response.name == "Test Cinema"
    assert response.address == "123 Test St"
    assert response.city == "Montreal"
    assert response.website == "https://example.com"


def test_output_data_allows_none_address_and_city() -> None:
    """Verify OutputData allows None for optional fields."""
    data = CreateCinemaUseCase.OutputData(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="Test Cinema",
    )
    assert data.address is None
    assert data.city is None
    assert data.website is None
