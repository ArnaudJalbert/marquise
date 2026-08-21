"""Tests for CLI commands with mocked MarquiseFactory."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from io import StringIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest

from marquise import (
    CinemaAlreadyExistsError,
    CinemaController,
    CinemaIdAlreadyExistsError,
    CinemaNotFoundError,
    CreateCinemaUseCase,
    DeleteCinemaUseCase,
    ListCinemasUseCase,
    SourceController,
    UpdateCinemaUseCase,
)
from marquise_cli.app import main


def invoke(args: list[str], input: str = "") -> SimpleNamespace:
    """Run CLI and capture process result."""
    stdout = StringIO()
    stderr = StringIO()
    with (
        patch("builtins.input", side_effect=input.splitlines()),
        redirect_stdout(stdout),
        redirect_stderr(stderr),
    ):
        try:
            exit_code = main(args)
        except SystemExit as error:
            exit_code = error.code or 0
    return SimpleNamespace(
        exit_code=exit_code,
        stdout=stdout.getvalue(),
        stderr=stderr.getvalue(),
    )


@pytest.fixture(autouse=True)
def _mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set required environment variables for MarquiseFactory creation."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")


@pytest.fixture
def mock_factory() -> MagicMock:
    """Provide a mocked MarquiseFactory."""
    factory = MagicMock()
    factory.__aenter__ = AsyncMock(return_value=factory)
    factory.__aexit__ = AsyncMock(return_value=False)
    return factory


# ---------------------------------------------------------------------------
# cinema create
# ---------------------------------------------------------------------------


def _mock_create_use_case(
    response: SimpleNamespace | None = None,
    error: Exception | None = None,
) -> MagicMock:
    """Provide a mocked create-cinema use case."""
    use_case = create_autospec(CreateCinemaUseCase, instance=True)
    use_case.execute = AsyncMock(side_effect=error, return_value=response)
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


# ---------------------------------------------------------------------------
# cinema delete
# ---------------------------------------------------------------------------


def _make_cinema_data(
    cinema_id: str = "cin-001",
    name: str = "Test Cinema",
    address: str | None = "123 Test St",
    city: str | None = "Montreal",
    website: str | None = "https://example.com",
) -> ListCinemasUseCase.CinemaData:
    """Helper to build a CinemaData instance for test setup."""
    return ListCinemasUseCase.CinemaData(
        id=cinema_id,
        name=name,
        address=address,
        city=city,
        website=website,
    )


@pytest.fixture
def mock_cinema_controller_for_delete() -> MagicMock:
    """Provide a mocked CinemaController with list methods."""
    controller = create_autospec(CinemaController, instance=True)
    controller.list_cinemas = AsyncMock()
    return controller


@pytest.fixture
def mock_delete_use_case() -> MagicMock:
    """Provide a mocked DeleteCinemaUseCase."""
    use_case = create_autospec(DeleteCinemaUseCase, instance=True)
    use_case.execute = AsyncMock()
    return use_case


@pytest.fixture
def mock_cinema_controller_for_update() -> MagicMock:
    """Provide a mocked CinemaController with cinema listing."""
    controller = create_autospec(CinemaController, instance=True)
    controller.list_cinemas = AsyncMock()
    return controller


def test_cinema_delete_success(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Verify cinema delete uses direct use-case execution after confirmation."""
    cinema = _make_cinema_data()
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[cinema], total=1)
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.delete_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Test Cinema")
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 0
    assert 'Cinema "Test Cinema" (ID: cin-001) deleted.' in result.stdout
    mock_delete_use_case.execute.assert_awaited_once_with(
        DeleteCinemaUseCase.InputData(cinema_id="cin-001")
    )
    mock_factory.__aenter__.assert_awaited_once()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_delete_name_mismatch(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Verify cinema delete aborts when confirmation name does not match."""
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[_make_cinema_data()], total=1)
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.delete_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=_make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Wrong Name")
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 1
    assert 'Name mismatch: expected "Test Cinema", got "Wrong Name"' in result.stderr
    mock_delete_use_case.execute.assert_not_awaited()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_delete_no_cinemas(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Verify cinema delete handles an empty cinema list."""
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[], total=0)
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with patch(
        "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 0
    assert "No cinemas available to delete." in result.stdout
    mock_delete_use_case.execute.assert_not_awaited()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_delete_list_failure(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Unexpected cinema-list errors propagate after factory cleanup."""
    mock_cinema_controller_for_delete.list_cinemas.side_effect = ValueError(
        "Database unavailable"
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        pytest.raises(ValueError, match="Database unavailable"),
    ):
        invoke(["cinema", "delete"])

    mock_delete_use_case.execute.assert_not_awaited()
    mock_factory.__aexit__.assert_awaited_once()


@pytest.mark.parametrize("selection", [None, "__exit__"])
def test_cinema_delete_cancelled_at_select(
    selection: str | None,
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Verify cinema delete handles selection cancellation."""
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[_make_cinema_data()], total=1)
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.delete_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=selection)
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_delete_use_case.execute.assert_not_awaited()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_delete_cancelled_at_confirmation(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
) -> None:
    """Verify cinema delete handles confirmation cancellation."""
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[_make_cinema_data()], total=1)
    )
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.delete_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=_make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value=None)
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_delete_use_case.execute.assert_not_awaited()
    mock_factory.__aexit__.assert_awaited_once()


@pytest.mark.parametrize(
    "error",
    [
        ValueError("cinema_id must not be empty"),
        CinemaNotFoundError("cinema was not found"),
    ],
)
def test_cinema_delete_failure(
    mock_factory: MagicMock,
    mock_cinema_controller_for_delete: MagicMock,
    mock_delete_use_case: MagicMock,
    error: Exception,
) -> None:
    """Every delete use-case error is shown and exits unsuccessfully."""
    mock_cinema_controller_for_delete.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[_make_cinema_data()], total=1)
    )
    mock_delete_use_case.execute.side_effect = error
    mock_factory.cinema = mock_cinema_controller_for_delete
    mock_factory.delete_cinema_use_case = mock_delete_use_case

    with (
        patch(
            "marquise_cli.cinema_commands.delete_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.delete_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(
            return_value=_make_cinema_data()
        )
        mock_q.text.return_value.ask_async = AsyncMock(return_value="Test Cinema")
        result = invoke(["cinema", "delete"])

    assert result.exit_code == 1
    assert f"Failed to delete cinema: {error}" in result.stderr
    mock_factory.__aexit__.assert_awaited_once()


# ---------------------------------------------------------------------------
# cinema list
# ---------------------------------------------------------------------------


def _make_list_mock_cinemas() -> list:
    """Build sample cinema data for list tests."""

    return [
        ListCinemasUseCase.CinemaData(
            id="cin-001",
            name="Cinema du Parc",
            address="123 Rue du Parc",
            city="Montreal",
            website="https://cinemaduparc.ca",
        ),
        ListCinemasUseCase.CinemaData(
            id="cin-002",
            name="Quartier Latin",
            address="345 Rue Ontario",
            city="Montreal",
        ),
    ]


def test_cinema_list_success(
    mock_factory: MagicMock,
) -> None:
    """Verify cinema list prints cinema names."""

    cinemas = _make_list_mock_cinemas()
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=cinemas, total=len(cinemas))
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.cinema_commands.list_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["cinema", "list"])

    assert result.exit_code == 0
    assert "Available cinemas:" in result.stdout
    assert "Cinema du Parc" in result.stdout
    assert "Quartier Latin" in result.stdout
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


def test_cinema_list_empty(
    mock_factory: MagicMock,
) -> None:
    """Verify cinema list shows 'No cinemas found' when empty."""

    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=[], total=0)
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.cinema_commands.list_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["cinema", "list"])

    assert result.exit_code == 0
    assert "No cinemas found." in result.stdout
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


def test_cinema_list_failure(
    mock_factory: MagicMock,
) -> None:
    """Unexpected list failures propagate after factory shutdown."""
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        side_effect=ValueError("Something went wrong")
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.cinema_commands.list_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        pytest.raises(ValueError, match="Something went wrong"),
    ):
        invoke(["cinema", "list"])

    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


def test_cinema_list_verbose(
    mock_factory: MagicMock,
) -> None:
    """Verify cinema list --verbose shows detailed table."""

    cinemas = _make_list_mock_cinemas()
    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=cinemas, total=len(cinemas))
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.cinema_commands.list_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["cinema", "list", "--verbose"])

    assert result.exit_code == 0
    assert "Available cinemas:" in result.stdout
    assert "cin-001" in result.stdout
    assert "123 Rue du Parc" in result.stdout
    assert "cin-002" in result.stdout
    assert "345 Rue Ontario" in result.stdout
    assert "cinemaduparc" in result.stdout
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


def test_cinema_list_with_name_filter(
    mock_factory: MagicMock,
) -> None:
    """Verify cinema list --name passes filter to controller."""

    mock_cinema_controller = create_autospec(CinemaController, instance=True)
    mock_cinema_controller.list = AsyncMock(
        return_value=ListCinemasUseCase.OutputData(cinemas=[], total=0)
    )
    mock_factory.cinema = mock_cinema_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.cinema_commands.list_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["cinema", "list", "--name", "Parc"])

    assert result.exit_code == 0
    mock_cinema_controller.list.assert_called_once_with(name="Parc")
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


# ---------------------------------------------------------------------------
# cinema update
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_update_use_case() -> MagicMock:
    """Provide a mocked UpdateCinemaUseCase."""
    use_case = create_autospec(UpdateCinemaUseCase, instance=True)
    use_case.execute = AsyncMock()
    return use_case


def _update_setup(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
    cinema: ListCinemasUseCase.CinemaData | None = None,
) -> dict[str, str | None]:
    """Wire update command collaborators with one cinema."""
    cinema = cinema or _make_cinema_data()
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[cinema], total=1)
    )
    mock_factory.cinema = mock_cinema_controller_for_update
    mock_factory.update_cinema_use_case = mock_update_use_case
    return asdict(cinema)


def test_cinema_update_success(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify cinema update executes use case with selected replacements."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    mock_update_use_case.execute.return_value = UpdateCinemaUseCase.OutputData(
        "cin-001", "Updated Name", "456 New Ave", "Montreal", "https://example.com"
    )
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["name", "address"]
        )
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=["Updated Name", "456 New Ave"]
        )
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    assert "Cinema updated:" in result.stdout
    mock_update_use_case.execute.assert_awaited_once_with(
        UpdateCinemaUseCase.InputData(
            "cin-001", "Updated Name", "456 New Ave", "Montreal", "https://example.com"
        )
    )
    mock_factory.__aenter__.assert_awaited_once()
    mock_factory.__aexit__.assert_awaited_once()


def test_cinema_update_clear_optional_field(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify cinema update supports clearing optional fields."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    mock_update_use_case.execute.return_value = UpdateCinemaUseCase.OutputData(
        "cin-001", "Test Cinema"
    )
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["address"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value="")
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    mock_update_use_case.execute.assert_awaited_once_with(
        UpdateCinemaUseCase.InputData(
            "cin-001", "Test Cinema", None, "Montreal", "https://example.com"
        )
    )


@pytest.mark.parametrize("selection", [None, "__exit__"])
def test_cinema_update_cancelled_at_select(
    selection: str | None,
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify cinema selection cancellation performs no update."""
    _update_setup(mock_factory, mock_cinema_controller_for_update, mock_update_use_case)
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=selection)
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_update_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize("fields", [None, []])
def test_cinema_update_cancelled_at_fields(
    fields: list[str] | None,
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify empty field selection performs no update."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=fields)
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    assert "No fields selected. Cancelled." in result.stdout
    mock_update_use_case.execute.assert_not_awaited()


def test_cinema_update_cancelled_at_value(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify field-value cancellation performs no update."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["name"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value=None)
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_update_use_case.execute.assert_not_awaited()


def test_cinema_update_no_cinemas(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify empty cinema list is reported clearly."""
    mock_cinema_controller_for_update.list_cinemas.return_value = (
        ListCinemasUseCase.OutputData(cinemas=[], total=0)
    )
    mock_factory.cinema = mock_cinema_controller_for_update
    mock_factory.update_cinema_use_case = mock_update_use_case
    with patch(
        "marquise_cli.cinema_commands.update_command.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["cinema", "update"])
    assert result.exit_code == 0
    assert "No cinemas available to update." in result.stdout
    mock_update_use_case.execute.assert_not_awaited()


@pytest.mark.parametrize(
    "error",
    [ValueError("name must not be empty"), CinemaNotFoundError("cinema was not found")],
)
def test_cinema_update_failure(
    error: Exception,
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify documented update errors reach stderr with exit code one."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    mock_update_use_case.execute.side_effect = error
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["name"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value="New Name")
        result = invoke(["cinema", "update"])
    assert result.exit_code == 1
    assert f"Failed to update cinema: {error}" in result.stderr


def test_cinema_update_unexpected_failure_propagates(
    mock_factory: MagicMock,
    mock_cinema_controller_for_update: MagicMock,
    mock_update_use_case: MagicMock,
) -> None:
    """Verify unexpected update failures propagate after factory cleanup."""
    cinema = _update_setup(
        mock_factory, mock_cinema_controller_for_update, mock_update_use_case
    )
    mock_update_use_case.execute.side_effect = RuntimeError("database unavailable")
    with (
        patch(
            "marquise_cli.cinema_commands.update_command.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.cinema_commands.update_command.questionary") as mock_q,
        pytest.raises(RuntimeError, match="database unavailable"),
    ):
        mock_q.select.return_value.ask_async = AsyncMock(return_value=cinema)
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=["name"])
        mock_q.text.return_value.ask_async = AsyncMock(return_value="New Name")
        invoke(["cinema", "update"])
    mock_factory.__aexit__.assert_awaited_once()


# ---------------------------------------------------------------------------
# source registry
# ---------------------------------------------------------------------------


def _make_registry_source_entry(
    name: str = "cinemacinema",
) -> SimpleNamespace:
    """Helper to build a SourceEntry for test setup."""

    return SimpleNamespace(
        name=name,
    )


def test_source_registry_show_sources(
    mock_factory: MagicMock,
) -> None:
    """Verify source registry command lists available sources with status."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[])
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.source_commands.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["source", "list-available"])

    assert result.exit_code == 0
    assert "cinemacinema" in result.stdout
    assert "—" in result.stdout
    mock_source_controller.list_registry_sources.assert_awaited_once()
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


def test_source_registry_empty(
    mock_factory: MagicMock,
) -> None:
    """Verify source registry shows empty message when no sources."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[])
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.source_commands.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["source", "list-available"])

    assert result.exit_code == 0
    assert "No sources registered in the registry." in result.stdout
    mock_source_controller.list_registry_sources.assert_awaited_once()
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


def test_source_registry_failure(
    mock_factory: MagicMock,
) -> None:
    """Verify source registry shows error on failure."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        side_effect=ValueError("Something went wrong")
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.source_commands.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["source", "list-available"])

    assert result.exit_code == 1
    assert "Failed to list registry sources: Something went wrong" in result.stderr


# ---------------------------------------------------------------------------
# source register
# ---------------------------------------------------------------------------


def test_source_register_new_source(
    mock_factory: MagicMock,
) -> None:
    """Verify source register creates a new source after prompting."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[])
    )
    mock_source_controller.create_source = AsyncMock(
        return_value=SimpleNamespace(
            name="cinemacinema",
            display_name="Cinéma Cinéma",
            description="Showtimes for Beaubien, du Parc, and du Musée",
        )
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.questionary") as mock_q,
    ):
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=[
                "Cinéma Cinéma",
                "Showtimes for Beaubien, du Parc, and du Musée",
            ]
        )

        result = invoke(["source", "register"])

    assert result.exit_code == 0
    assert "cinemacinema" in result.stdout
    assert "new" in result.stdout
    assert "Created: cinemacinema" in result.stdout
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()
    mock_source_controller.create_source.assert_awaited_once_with(
        name="cinemacinema",
        display_name="Cinéma Cinéma",
        description="Showtimes for Beaubien, du Parc, and du Musée",
    )


def test_source_register_all_existing(
    mock_factory: MagicMock,
) -> None:
    """Verify source register shows all done when nothing new to add."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(
            sources=[
                SimpleNamespace(
                    name="cinemacinema",
                    display_name="Cinéma Cinéma",
                )
            ]
        )
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.source_commands.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["source", "register"])

    assert result.exit_code == 0
    assert "already registered" in result.stdout
    assert "All registry sources are already" in result.stdout
    mock_source_controller.create_source.assert_not_awaited()
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()


def test_source_register_failure(
    mock_factory: MagicMock,
) -> None:
    """Verify source register shows error when create_source fails."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[])
    )
    mock_source_controller.create_source = AsyncMock(
        side_effect=ValueError("SourceAlreadyExistsError")
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.questionary") as mock_q,
    ):
        mock_q.text.return_value.ask_async = AsyncMock(
            side_effect=["Cinéma Cinéma", "Showtimes description"]
        )

        result = invoke(["source", "register"])

    assert result.exit_code == 0
    assert "Failed: SourceAlreadyExistsError" in result.stderr
    assert "  Failed: SourceAlreadyExistsError" in result.stderr


# ---------------------------------------------------------------------------
# source unregister
# ---------------------------------------------------------------------------


def test_source_unregister_success(
    mock_factory: MagicMock,
) -> None:
    """Verify source unregister removes selected sources after confirmation."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(
            sources=[
                SimpleNamespace(
                    name="cinemacinema",
                    display_name="Cinéma Cinéma",
                )
            ]
        )
    )
    mock_source_controller.delete_source = AsyncMock(
        return_value=SimpleNamespace(source_name="cinemacinema")
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.questionary") as mock_q,
    ):
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=True)

        result = invoke(["source", "unregister"])

    assert result.exit_code == 0
    assert "in registry" in result.stdout
    assert "Removed: cinemacinema" in result.stdout
    mock_factory.initialize.assert_called_once()
    mock_factory.shutdown.assert_called_once()
    mock_source_controller.delete_source.assert_awaited_once_with(
        source_name="cinemacinema",
    )


def test_source_unregister_no_selection(
    mock_factory: MagicMock,
) -> None:
    """Verify source unregister bails when no sources are selected."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(
            sources=[
                SimpleNamespace(
                    name="cinemacinema",
                    display_name="Cinéma Cinéma",
                )
            ]
        )
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.questionary") as mock_q,
    ):
        mock_q.checkbox.return_value.ask_async = AsyncMock(return_value=[])

        result = invoke(["source", "unregister"])

    assert result.exit_code == 0
    assert "No sources selected." in result.stdout
    mock_source_controller.delete_source.assert_not_awaited()


def test_source_unregister_empty_db(
    mock_factory: MagicMock,
) -> None:
    """Verify source unregister bails when database has no sources."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[])
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with patch(
        "marquise_cli.source_commands.MarquiseFactory",
        return_value=mock_factory,
    ):
        result = invoke(["source", "unregister"])

    assert result.exit_code == 0
    assert "No sources registered in the database." in result.stdout
    mock_source_controller.delete_source.assert_not_awaited()


def test_source_unregister_cancelled_at_confirm(
    mock_factory: MagicMock,
) -> None:
    """Verify source unregister bails when user declines confirmation."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(
            sources=[
                SimpleNamespace(
                    name="cinemacinema",
                    display_name="Cinéma Cinéma",
                )
            ]
        )
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.questionary") as mock_q,
    ):
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=False)

        result = invoke(["source", "unregister"])

    assert result.exit_code == 0
    assert "Cancelled." in result.stdout
    mock_source_controller.delete_source.assert_not_awaited()


def test_source_unregister_partial_failure(
    mock_factory: MagicMock,
) -> None:
    """Verify source unregister shows per-source errors on failure."""
    mock_source_controller = create_autospec(SourceController, instance=True)
    mock_source_controller.list_registry_sources = AsyncMock(
        return_value=SimpleNamespace(sources=[_make_registry_source_entry()])
    )
    mock_source_controller.list_sources = AsyncMock(
        return_value=SimpleNamespace(
            sources=[
                SimpleNamespace(
                    name="cinemacinema",
                    display_name="Cinéma Cinéma",
                )
            ]
        )
    )
    mock_source_controller.delete_source = AsyncMock(
        side_effect=ValueError("Something went wrong")
    )
    mock_factory.source = mock_source_controller
    mock_factory.initialize = AsyncMock()
    mock_factory.shutdown = AsyncMock()

    with (
        patch(
            "marquise_cli.source_commands.MarquiseFactory",
            return_value=mock_factory,
        ),
        patch("marquise_cli.source_commands.questionary") as mock_q,
    ):
        mock_q.checkbox.return_value.ask_async = AsyncMock(
            return_value=["cinemacinema"]
        )
        mock_q.confirm.return_value.ask_async = AsyncMock(return_value=True)

        result = invoke(["source", "unregister"])

    assert result.exit_code == 0
    assert "Failed: Something went wrong" in result.stderr
