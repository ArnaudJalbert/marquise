"""Tests for cinema create CLI command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from marquise import (
    AssignSourceUseCase,
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CreateCinemaUseCase,
)
from marquise_cli.cinema_commands.create_command import run_create


def _mock_create_use_case(
    response: SimpleNamespace | None = None,
    error: Exception | None = None,
) -> MagicMock:
    """Provide a mocked create-cinema use case."""
    use_case = create_autospec(CreateCinemaUseCase, instance=True)
    use_case.execute = AsyncMock(side_effect=error, return_value=response)
    use_case.InputData = CreateCinemaUseCase.InputData
    return use_case


def _created_cinema() -> CreateCinemaUseCase.OutputData:
    """Provide cinema output for create command tests."""
    return CreateCinemaUseCase.OutputData(
        id="cin-001",
        name="Test Cinema",
        address="123 Test St",
        city="Montreal",
        website="https://example.com",
    )


@pytest.mark.asyncio
async def test_cinema_create_success(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify cinema create uses the direct use case and prints details."""
    use_case = _mock_create_use_case(response=_created_cinema())
    mock_factory.cinemas.create_cinema_use_case = use_case

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
    use_case.execute.assert_awaited_once()
    request = use_case.execute.call_args.args[0]
    assert isinstance(request, CreateCinemaUseCase.InputData)
    assert request.name == "Test Cinema"
    assert request.address == "123 Test St"
    assert request.city == "Montreal"
    assert request.website == "https://example.com"


@pytest.mark.asyncio
async def test_cinema_create_assigns_source_after_success(
    mock_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify successful creation can assign a selected source."""
    use_case = _mock_create_use_case(response=_created_cinema())
    assign_use_case = create_autospec(AssignSourceUseCase, instance=True)
    assign_use_case.execute = AsyncMock(
        return_value=SimpleNamespace(cinema_id="cin-001", source_name="cineplex")
    )
    mock_factory.cinemas.create_cinema_use_case = use_case
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
    request = use_case.execute.call_args.args[0]
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
    use_case = _mock_create_use_case(response=_created_cinema())
    assign_use_case = create_autospec(AssignSourceUseCase, instance=True)
    mock_factory.cinemas.create_cinema_use_case = use_case
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
    use_case = _mock_create_use_case(response=_created_cinema())
    assign_use_case = create_autospec(AssignSourceUseCase, instance=True)
    assign_use_case.execute = AsyncMock(side_effect=ValueError("Source unavailable"))
    mock_factory.cinemas.create_cinema_use_case = use_case
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
    """Every create use-case error is shown and exits unsuccessfully."""
    use_case = _mock_create_use_case(error=error)
    mock_factory.cinemas.create_cinema_use_case = use_case

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
    mock_factory.cinemas.create_cinema_use_case = _mock_create_use_case(
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
