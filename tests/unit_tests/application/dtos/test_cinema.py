"""Tests for application DTOs."""

from __future__ import annotations

import pytest

from marquise.application.dtos.cinema import CreateCinemaRequest, CreateCinemaResponse


def test_create_cinema_request_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name must not be empty"):
        CreateCinemaRequest(name="", address="123 Test St", city="Montreal")


def test_create_cinema_response_creation() -> None:
    response = CreateCinemaResponse(
        id="550e8400-e29b-41d4-a716-446655440000",
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
    )
    assert response.id == "550e8400-e29b-41d4-a716-446655440000"
    assert response.name == "Test Cinema"
    assert response.address == "123 Test St"
    assert response.city == "Montreal"
