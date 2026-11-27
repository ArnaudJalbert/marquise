"""Tests for application DTOs."""

from __future__ import annotations

import pytest

from marquise.application.use_cases.create_cinema import CreateCinemaCommand


def test_input_data_rejects_empty_name() -> None:
    """Verify InputData rejects an empty cinema name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateCinemaCommand.InputData(
            name="",
            address="123 Test St",
            city="Montreal",
            website="https://example.com",
        )


def test_input_data_rejects_whitespace_name() -> None:
    """Verify InputData rejects a whitespace-only name."""
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateCinemaCommand.InputData(
            name="   ",
            address="123 Test St",
            city="Montreal",
            website="https://example.com",
        )


def test_input_data_rejects_empty_address_when_provided() -> None:
    """Verify InputData rejects an empty address string."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        CreateCinemaCommand.InputData(
            name="Test Cinema", address="", website="https://example.com"
        )


def test_input_data_rejects_whitespace_address_when_provided() -> None:
    """Verify InputData rejects a whitespace-only address."""
    with pytest.raises(ValueError, match="address must not be empty when provided"):
        CreateCinemaCommand.InputData(
            name="Test Cinema", address="   ", website="https://example.com"
        )


def test_input_data_rejects_empty_city_when_provided() -> None:
    """Verify InputData rejects an empty city string."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        CreateCinemaCommand.InputData(
            name="Test Cinema",
            address="123 Test St",
            city="",
            website="https://example.com",
        )


def test_input_data_rejects_whitespace_city_when_provided() -> None:
    """Verify InputData rejects a whitespace-only city."""
    with pytest.raises(ValueError, match="city must not be empty when provided"):
        CreateCinemaCommand.InputData(
            name="Test Cinema",
            address="123 Test St",
            city="   ",
            website="https://example.com",
        )


def test_input_data_allows_none_address_and_city() -> None:
    """Verify InputData allows None for optional fields."""
    data = CreateCinemaCommand.InputData(name="Test Cinema")
    assert data.address is None
    assert data.city is None
    assert data.website is None


def test_input_data_rejects_empty_website_when_provided() -> None:
    """Verify InputData rejects an empty website string."""
    with pytest.raises(ValueError, match="website must not be empty when provided"):
        CreateCinemaCommand.InputData(name="Test Cinema", website="")


def test_input_data_rejects_whitespace_website_when_provided() -> None:
    """Verify InputData rejects a whitespace-only website."""
    with pytest.raises(ValueError, match="website must not be empty when provided"):
        CreateCinemaCommand.InputData(name="Test Cinema", website="   ")


@pytest.mark.parametrize("field", ["name", "address", "city", "website"])
def test_input_data_rejects_non_string_field(field: str) -> None:
    """InputData rejects a field that is not a string."""
    fields = {"name": "Test Cinema", field: 42}

    with pytest.raises(TypeError, match=f"{field} must be a string"):
        CreateCinemaCommand.InputData(**fields)
