"""Application failures are reported at the CLI command boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from importlib import import_module
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from conftest import make_cinema_data
from marquise import (
    AssignSourceUseCase,
    CinemaNotFoundError,
    CinemaSourceAssignmentAlreadyExistsError,
    CinemaSourceAssignmentNotFoundError,
    GetCinemaSourceUseCase,
    ImportScreeningsCommand,
    MarquiseFactory,
    SourceNotFoundError,
    UnassignSourceUseCase,
)
from marquise_cli.app import main


@dataclass(frozen=True)
class Command:
    """A selected CLI command and its failing application dependency."""

    argv: tuple[str, ...]
    factory: MagicMock
    use_case: MagicMock


@pytest.fixture
def command(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Command:
    """Supply interactive selections and a factory without external services."""
    group, name, attribute, use_case_type = request.param
    module = import_module(f"marquise_cli.{group}_commands.{name}_command")
    factory = _stub_factory()
    use_case = create_autospec(use_case_type, instance=True)
    use_case.InputData = use_case_type.InputData
    setattr(factory, attribute, use_case)
    monkeypatch.setattr(module, "MarquiseFactory", lambda: factory)
    _stub_selections(module.__name__, monkeypatch)
    return Command((group, name), factory, use_case)


def _stub_factory() -> MagicMock:
    factory = create_autospec(MarquiseFactory, instance=True)
    source = create_autospec(GetCinemaSourceUseCase, instance=True)
    source.InputData = GetCinemaSourceUseCase.InputData
    source.execute.return_value = GetCinemaSourceUseCase.OutputData(
        "cin-001", "cineplex", "Cineplex"
    )
    factory.get_cinema_source_use_case = source
    return factory


def _stub_selections(module_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        f"{module_name}.select_cinema", AsyncMock(return_value=make_cinema_data())
    )
    if module_name.endswith(".assign_command"):
        monkeypatch.setattr(
            f"{module_name}.select_source", AsyncMock(return_value="cineplex")
        )
    elif module_name.endswith("cinema_command"):
        monkeypatch.setattr(
            f"{module_name}._select_date_range",
            AsyncMock(return_value=(date(2026, 11, 14), date(2026, 11, 15))),
        )


IMPORT_LOOKUP = (
    "import",
    "cinema",
    "get_cinema_source_use_case",
    GetCinemaSourceUseCase,
)
IMPORT = ("import", "cinema", "import_screenings_use_case", ImportScreeningsCommand)
ASSIGN = ("source", "assign", "assign_source_use_case", AssignSourceUseCase)
UNASSIGN = ("source", "unassign", "unassign_source_use_case", UnassignSourceUseCase)


@pytest.mark.parametrize(
    ("command", "error"),
    [
        (IMPORT_LOOKUP, CinemaSourceAssignmentNotFoundError("No source assigned")),
        (IMPORT, CinemaSourceAssignmentNotFoundError("Assignment removed")),
        (UNASSIGN, CinemaSourceAssignmentNotFoundError("No assignment to remove")),
        (ASSIGN, CinemaNotFoundError("Cinema no longer exists")),
        (ASSIGN, SourceNotFoundError("Source no longer exists")),
        (ASSIGN, CinemaSourceAssignmentAlreadyExistsError("Already assigned")),
    ],
    indirect=["command"],
)
def test_documented_error_prints_message_and_exits_nonzero(
    command: Command, error: Exception, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each documented failure produces a readable message and unsuccessful exit."""
    command.use_case.execute.side_effect = error
    with pytest.raises(SystemExit) as failure:
        main(command.argv)
    assert failure.value.code == 1
    assert str(error) in capsys.readouterr().err
    command.factory.shutdown.assert_awaited_once()


@pytest.mark.parametrize(
    "command", [IMPORT_LOOKUP, IMPORT, ASSIGN, UNASSIGN], indirect=True
)
@pytest.mark.parametrize("error_type", [RuntimeError, ValueError, SourceNotFoundError])
def test_unlisted_errors_escape(command: Command, error_type: type[Exception]) -> None:
    """Unexpected application and programming failures keep their traceback."""
    if command.argv == ("source", "assign") and error_type is SourceNotFoundError:
        error_type = CinemaSourceAssignmentNotFoundError
    error = error_type("Unexpected failure")
    command.use_case.execute.side_effect = error
    with pytest.raises(error_type) as failure:
        main(command.argv)
    assert failure.value is error
    command.factory.shutdown.assert_awaited_once()
