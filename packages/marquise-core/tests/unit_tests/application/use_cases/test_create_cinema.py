"""Tests for CreateCinemaCommand."""

from __future__ import annotations

import re
from unittest.mock import create_autospec

import pytest

from marquise.application.exceptions import (
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
)
from marquise.application.repositories import CinemaRepository
from marquise.application.use_cases.create_cinema import CreateCinemaCommand
from marquise.domain.entities import Cinema
from marquise.domain.value_objects import CinemaId


@pytest.fixture
def cinema_repository() -> CinemaRepository:
    """Provide a repository with no matching cinema that saves what it gets."""
    cinema_repository = create_autospec(CinemaRepository, instance=True)
    cinema_repository.find_by_name_and_address.return_value = None
    cinema_repository.save.side_effect = lambda cinema: cinema
    return cinema_repository


@pytest.fixture
def command(cinema_repository: CinemaRepository) -> CreateCinemaCommand:
    """Provide the command over the mocked repository."""
    return CreateCinemaCommand(cinema_repository=cinema_repository)


@pytest.fixture
def input_data() -> CreateCinemaCommand.InputData:
    """Provide input for a cinema with every field set."""
    return CreateCinemaCommand.InputData(
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )


@pytest.mark.asyncio
async def test_create_cinema_saves_cinema_and_returns_its_id(
    command: CreateCinemaCommand,
    cinema_repository: CinemaRepository,
    input_data: CreateCinemaCommand.InputData,
) -> None:
    """The command saves the input as a cinema and returns only its new ID."""
    result = await command.execute(input_data)

    saved = cinema_repository.save.await_args.args[0]
    assert saved == Cinema(
        id=saved.id,
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )
    assert result == CreateCinemaCommand.OutputData(cinema_id=saved.id.value)
    assert re.fullmatch(r"[0-9a-f]{32}", result.cinema_id)
    cinema_repository.find_by_name_and_address.assert_awaited_once_with(
        name="Test Cinema", address="123 Test St"
    )


@pytest.mark.asyncio
async def test_create_cinema_saves_absent_optional_fields_as_none(
    command: CreateCinemaCommand, cinema_repository: CinemaRepository
) -> None:
    """A cinema created with only a name is saved with no address, city or website."""
    await command.execute(command.InputData(name="Test Cinema"))

    saved = cinema_repository.save.await_args.args[0]
    assert (saved.address, saved.city, saved.website) == (None, None, None)


@pytest.mark.parametrize("field", ["name", "address", "city", "website"])
@pytest.mark.asyncio
async def test_create_cinema_rejects_blank_field(
    command: CreateCinemaCommand, field: str
) -> None:
    """A blank name, or a blank optional field when given, is rejected."""
    fields = {"name": "Test Cinema", field: "   "}

    with pytest.raises(ValueError, match=f"{field} must not be empty"):
        await command.execute(command.InputData(**fields))


@pytest.mark.parametrize("field", ["name", "address", "city", "website"])
@pytest.mark.asyncio
async def test_create_cinema_rejects_non_string_field(
    command: CreateCinemaCommand, field: str
) -> None:
    """A field that is not a string is rejected."""
    fields = {"name": "Test Cinema", field: 42}

    with pytest.raises(TypeError, match=f"{field} must be a string"):
        await command.execute(command.InputData(**fields))


@pytest.mark.asyncio
async def test_create_cinema_rejects_duplicate_name_and_address(
    command: CreateCinemaCommand,
    cinema_repository: CinemaRepository,
    input_data: CreateCinemaCommand.InputData,
) -> None:
    """A cinema with the same name and address stops the command before saving."""
    cinema_repository.find_by_name_and_address.return_value = Cinema(
        id=CinemaId(value="existing"), name="Test Cinema", address="123 Test St"
    )

    with pytest.raises(
        CinemaAlreadyExistsError,
        match=r"^A cinema with name 'Test Cinema' already exists\.$",
    ):
        await command.execute(input_data)

    cinema_repository.save.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_cinema_raises_when_id_collides(
    command: CreateCinemaCommand,
    cinema_repository: CinemaRepository,
    input_data: CreateCinemaCommand.InputData,
) -> None:
    """A generated ID that already exists raises the repository's error."""
    cinema_repository.save.side_effect = CinemaIdAlreadyExistsError("already exists")

    with pytest.raises(CinemaIdAlreadyExistsError, match="already exists"):
        await command.execute(input_data)
