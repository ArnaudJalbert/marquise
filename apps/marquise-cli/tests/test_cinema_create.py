"""Tests for cinema create CLI command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from conftest import invoke
from marquise import (
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CreateCinemaUseCase,
    SourceController,
)


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


def test_cinema_create_success(mock_factory: MagicMock) -> None:
    """Verify cinema create uses the direct use case and prints details."""
    use_case = _mock_create_use_case(response=_created_cinema())
    mock_factory.create_cinema_use_case = use_case

    with (
        patch(
            "marquise_cli.cinema_commands.create_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch(
            "marquise_cli.cinema_commands.create_command.questionary.confirm"
        ) as confirm,
    ):
        confirm.return_value.ask_async = AsyncMock(return_value=False)
        result = invoke(
            ["cinema", "create"],
            input="Test Cinema\n123 Test St\nMontreal\nhttps://example.com\n",
        )

    assert result.exit_code == 0
    assert "Cinema created:" in result.stdout
    assert "cin-001" in result.stdout
    assert "Test Cinema" in result.stdout
    use_case.execute.assert_awaited_once()
    request = use_case.execute.call_args.args[0]
    assert isinstance(request, CreateCinemaUseCase.InputData)
    assert request.name == "Test Cinema"
    assert request.address == "123 Test St"
    assert request.city == "Montreal"
    assert request.website == "https://example.com"
    mock_factory.__aenter__.assert_awaited_once()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_create_assigns_source_after_success(mock_factory: MagicMock) -> None:
    """Verify successful creation can assign a selected source."""
    use_case = _mock_create_use_case(response=_created_cinema())
    source = create_autospec(SourceController, instance=True)
    source.assign_source = AsyncMock(
        return_value=SimpleNamespace(cinema_id="cin-001", source_name="cineplex")
    )
    mock_factory.create_cinema_use_case = use_case
    mock_factory.source = source

    with (
        patch(
            "marquise_cli.cinema_commands.create_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch(
            "marquise_cli.cinema_commands.create_command.questionary.confirm"
        ) as confirm,
        patch(
            "marquise_cli.cinema_commands.create_command.select_source",
            new=AsyncMock(return_value="cineplex"),
        ),
    ):
        confirm.return_value.ask_async = AsyncMock(return_value=True)
        result = invoke(
            ["cinema", "create"],
            input="Test Cinema\n\n\n\n",
        )

    assert result.exit_code == 0
    mock_factory.__aenter__.assert_awaited_once()
    mock_factory.__aexit__.assert_awaited_once()
    assert "Source assigned:" in result.stdout
    request = use_case.execute.call_args.args[0]
    assert request.address is None
    assert request.city is None
    assert request.website is None
    source.assign_source.assert_awaited_once_with(
        cinema_id="cin-001", source_name="cineplex"
    )


def test_cinema_create_declines_source_assignment(mock_factory: MagicMock) -> None:
    """Verify declining source assignment leaves cinema created."""
    use_case = _mock_create_use_case(response=_created_cinema())
    source = create_autospec(SourceController, instance=True)
    source.assign_source = AsyncMock()
    mock_factory.create_cinema_use_case = use_case
    mock_factory.source = source

    with (
        patch(
            "marquise_cli.cinema_commands.create_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch(
            "marquise_cli.cinema_commands.create_command.questionary.confirm"
        ) as confirm,
        patch(
            "marquise_cli.cinema_commands.create_command.select_source",
            new=AsyncMock(),
        ) as select_source,
    ):
        confirm.return_value.ask_async = AsyncMock(return_value=False)
        result = invoke(["cinema", "create"], input="Test Cinema\n\n\n\n")

    assert result.exit_code == 0
    mock_factory.__aenter__.assert_awaited_once()
    mock_factory.__aexit__.assert_awaited_once()
    select_source.assert_not_awaited()
    source.assign_source.assert_not_awaited()


def test_cinema_create_assignment_failure(mock_factory: MagicMock) -> None:
    """Verify source assignment errors are reported after creation."""
    use_case = _mock_create_use_case(response=_created_cinema())
    source = create_autospec(SourceController, instance=True)
    source.assign_source = AsyncMock(side_effect=ValueError("Source unavailable"))
    mock_factory.create_cinema_use_case = use_case
    mock_factory.source = source

    with (
        patch(
            "marquise_cli.cinema_commands.create_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch(
            "marquise_cli.cinema_commands.create_command.questionary.confirm"
        ) as confirm,
        patch(
            "marquise_cli.cinema_commands.create_command.select_source",
            new=AsyncMock(return_value="cineplex"),
        ),
    ):
        confirm.return_value.ask_async = AsyncMock(return_value=True)
        result = invoke(["cinema", "create"], input="Test Cinema\n\n\n\n")

    assert result.exit_code == 1
    assert (
        "There was an error when assigning the source to the cinema: Source unavailable"
    ) in result.stderr
    mock_factory.__aexit__.assert_awaited_once()


@pytest.mark.parametrize(
    "error",
    [
        ValueError("name must not be empty"),
        CinemaAlreadyExistsError("cinema already exists"),
        CinemaIdAlreadyExistsError("cinema ID already exists"),
    ],
)
def test_cinema_create_failure(mock_factory: MagicMock, error: Exception) -> None:
    """Every create use-case error is shown and exits unsuccessfully."""
    use_case = _mock_create_use_case(error=error)
    mock_factory.create_cinema_use_case = use_case

    with patch(
        "marquise_cli.cinema_commands.create_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(
            ["cinema", "create"],
            input="Test Cinema\n123 Test St\nMontreal\nhttps://example.com\n",
        )

    assert result.exit_code == 1
    assert f"There was an error when creating the cinema: {error}" in result.stderr
    assert "Created" not in result.stdout
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_create_unexpected_failure_propagates(mock_factory: MagicMock) -> None:
    """Unexpected create failures propagate after factory cleanup."""
    mock_factory.create_cinema_use_case = _mock_create_use_case(
        error=RuntimeError("database unavailable")
    )

    with (
        patch(
            "marquise_cli.cinema_commands.create_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        pytest.raises(RuntimeError, match="database unavailable"),
    ):
        invoke(["cinema", "create"], input="Test Cinema\n\n\n\n")

    mock_factory.__aexit__.assert_awaited_once()
