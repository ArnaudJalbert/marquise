"""Tests for cinema create CLI command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from marquise import (
    AssignSourceUseCase,
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CreateCinemaCommand,
    GetCinemaQuery,
)
from marquise_cli.cinema_commands.create_command import run_create


def _mock_create_command(
    response: CreateCinemaCommand.OutputData | None = None,
    error: Exception | None = None,
) -> MagicMock:
    """Provide a mocked create-cinema command."""
    command = create_autospec(CreateCinemaCommand, instance=True)
    command.execute = AsyncMock(side_effect=error, return_value=response)
    command.InputData = CreateCinemaCommand.InputData
    return command


def _created_cinema() -> CreateCinemaCommand.OutputData:
    """Provide the created cinema's ID for create command tests."""
    return CreateCinemaCommand.OutputData(cinema_id="cin-001")


def _mock_get_cinema_query() -> MagicMock:
    """Provide a mocked query that reads the created cinema back."""
    query = create_autospec(GetCinemaQuery, instance=True)
    query.execute = AsyncMock(
        return_value=GetCinemaQuery.OutputData(
            id="cin-001",
            name="Test Cinema",
            address="123 Test St",
            city="Montreal",
            website="https://example.com",
        )
    )
    query.InputData = GetCinemaQuery.InputData
    return query


@pytest.mark.asyncio
async def test_cinema_create_success(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Cinema create runs the command, then prints the cinema read back by ID."""
    create_command = _mock_create_command(response=_created_cinema())
    mock_factory.cinemas.create_cinema_command = create_command
    mock_factory.cinemas.get_cinema_query = _mock_get_cinema_query()

    with patch(
        "marquise_cli.cinema_commands.create_command.questionary.confirm"
    ) as confirm:
        confirm.return_value.ask_async = AsyncMock(return_value=False)
        await run_create(
            mock_factory,
            name="Test Cinema",
            address="123 Test St",
            city="Montreal",
            website="https://example.com",
        )

    captured = capsys.readouterr()
    assert "Cinema created:" in captured.out
    assert "cin-001" in captured.out
    assert "Test Cinema" in captured.out
    create_command.execute.assert_awaited_once()
    request = create_command.execute.call_args.args[0]
    assert isinstance(request, CreateCinemaCommand.InputData)
    assert request.name == "Test Cinema"
    assert request.address == "123 Test St"
    assert request.city == "Montreal"
    assert request.website == "https://example.com"
    query_request = mock_factory.cinemas.get_cinema_query.execute.call_args.args[0]
    assert query_request == GetCinemaQuery.InputData(cinema_id="cin-001")


@pytest.mark.asyncio
async def test_cinema_create_assigns_source_after_success(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify successful creation can assign a selected source."""
    create_command = _mock_create_command(response=_created_cinema())
    assign_use_case = create_autospec(AssignSourceUseCase, instance=True)
    assign_use_case.execute = AsyncMock(
        return_value=SimpleNamespace(cinema_id="cin-001", source_name="cineplex")
    )
    mock_factory.cinemas.create_cinema_command = create_command
    mock_factory.cinemas.get_cinema_query = _mock_get_cinema_query()
    mock_factory.sources.assign_source_use_case = assign_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.create_command.questionary.confirm"
        ) as confirm,
        patch(
            "marquise_cli.cinema_commands.create_command.select_source",
            new=AsyncMock(return_value="cineplex"),
        ),
    ):
        confirm.return_value.ask_async = AsyncMock(return_value=True)
        await run_create(
            mock_factory,
            name="Test Cinema",
            address=None,
            city=None,
            website=None,
        )

    captured = capsys.readouterr()
    assert "Source assigned:" in captured.out
    request = create_command.execute.call_args.args[0]
    assert request.address is None
    assert request.city is None
    assert request.website is None
    assign_use_case.InputData.assert_called_once_with(
        cinema_id="cin-001", source_name="cineplex"
    )
    assign_use_case.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_cinema_create_declines_source_assignment(
    mock_factory: MagicMock,
) -> None:
    """Verify declining source assignment leaves cinema created."""
    create_command = _mock_create_command(response=_created_cinema())
    assign_use_case = create_autospec(AssignSourceUseCase, instance=True)
    mock_factory.cinemas.create_cinema_command = create_command
    mock_factory.cinemas.get_cinema_query = _mock_get_cinema_query()
    mock_factory.sources.assign_source_use_case = assign_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.create_command.questionary.confirm"
        ) as confirm,
        patch(
            "marquise_cli.cinema_commands.create_command.select_source",
            new=AsyncMock(),
        ) as select_source,
    ):
        confirm.return_value.ask_async = AsyncMock(return_value=False)
        await run_create(
            mock_factory,
            name="Test Cinema",
            address=None,
            city=None,
            website=None,
        )

    select_source.assert_not_awaited()
    assign_use_case.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_cinema_create_assignment_failure(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify source assignment errors are reported after creation."""
    create_command = _mock_create_command(response=_created_cinema())
    assign_use_case = create_autospec(AssignSourceUseCase, instance=True)
    assign_use_case.execute = AsyncMock(side_effect=ValueError("Source unavailable"))
    mock_factory.cinemas.create_cinema_command = create_command
    mock_factory.cinemas.get_cinema_query = _mock_get_cinema_query()
    mock_factory.sources.assign_source_use_case = assign_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.create_command.questionary.confirm"
        ) as confirm,
        patch(
            "marquise_cli.cinema_commands.create_command.select_source",
            new=AsyncMock(return_value="cineplex"),
        ),
        pytest.raises(SystemExit),
    ):
        confirm.return_value.ask_async = AsyncMock(return_value=True)
        await run_create(
            mock_factory,
            name="Test Cinema",
            address=None,
            city=None,
            website=None,
        )

    captured = capsys.readouterr()
    assert (
        "There was an error when assigning the source to the cinema: Source unavailable"
    ) in captured.err


@pytest.mark.parametrize(
    "error",
    [
        ValueError("name must not be empty"),
        CinemaAlreadyExistsError("cinema already exists"),
        CinemaIdAlreadyExistsError("cinema ID already exists"),
    ],
)
@pytest.mark.asyncio
async def test_cinema_create_failure(
    mock_factory: MagicMock,
    error: Exception,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every create command error is shown and exits unsuccessfully."""
    create_command = _mock_create_command(error=error)
    mock_factory.cinemas.create_cinema_command = create_command
    mock_factory.cinemas.get_cinema_query = _mock_get_cinema_query()

    with pytest.raises(SystemExit):
        await run_create(
            mock_factory,
            name="Test Cinema",
            address="123 Test St",
            city="Montreal",
            website="https://example.com",
        )

    captured = capsys.readouterr()
    assert f"There was an error when creating the cinema: {error}" in captured.err
    assert "Created" not in captured.out


@pytest.mark.asyncio
async def test_cinema_create_unexpected_failure_propagates(
    mock_factory: MagicMock,
) -> None:
    """Unexpected create failures propagate after factory cleanup."""
    mock_factory.cinemas.create_cinema_command = _mock_create_command(
        error=RuntimeError("database unavailable")
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        await run_create(
            mock_factory,
            name="Test Cinema",
            address=None,
            city=None,
            website=None,
        )
