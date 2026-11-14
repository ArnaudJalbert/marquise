"""Application failures are reported at the CLI command boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from types import ModuleType
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
    ListCinemasUseCase,
    MarquiseFactory,
    SourceNotFoundError,
    UnassignSourceUseCase,
)
from marquise_cli.app import main
from marquise_cli.import_commands import cinema_command
from marquise_cli.source_commands import assign_command, unassign_command


@dataclass(frozen=True)
class Command:
    """A selected CLI command and its failing application dependency."""

    argv: tuple[str, ...]
    factory: MagicMock
    use_case: MagicMock


@pytest.fixture
def command(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Command:
    """Supply interactive selections and a factory without external services."""
    argv, module, attribute, use_case_type, selections = request.param
    factory = _stub_factory()
    use_case = create_autospec(use_case_type, instance=True)
    use_case.InputData = use_case_type.InputData
    setattr(factory, attribute, use_case)
    monkeypatch.setattr(module, "MarquiseFactory", lambda: factory)
    _stub_selections(module, selections, monkeypatch)
    return Command(argv, factory, use_case)


def _stub_factory() -> MagicMock:
    factory = create_autospec(MarquiseFactory, instance=True)
    source = create_autospec(GetCinemaSourceUseCase, instance=True)
    source.InputData = GetCinemaSourceUseCase.InputData
    source.execute.return_value = GetCinemaSourceUseCase.OutputData(
        "cin-001", "cineplex", "Cineplex"
    )
    factory.get_cinema_source_use_case = source
    return factory


def _stub_selections(
    module: ModuleType,
    selections: dict[str, ListCinemasUseCase.CinemaData | str | tuple[date, date]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for attribute, selection in selections.items():
        monkeypatch.setattr(module, attribute, AsyncMock(return_value=selection))


IMPORT_SELECTIONS = {
    "select_cinema": make_cinema_data(),
    "_select_date_range": (date(2026, 11, 14), date(2026, 11, 15)),
}
IMPORT_LOOKUP = (
    ("import", "cinema"),
    cinema_command,
    "get_cinema_source_use_case",
    GetCinemaSourceUseCase,
    IMPORT_SELECTIONS,
)
IMPORT = (
    ("import", "cinema"),
    cinema_command,
    "import_screenings_use_case",
    ImportScreeningsCommand,
    IMPORT_SELECTIONS,
)
ASSIGN = (
    ("source", "assign"),
    assign_command,
    "assign_source_use_case",
    AssignSourceUseCase,
    {"select_cinema": make_cinema_data(), "select_source": "cineplex"},
)
UNASSIGN = (
    ("source", "unassign"),
    unassign_command,
    "unassign_source_use_case",
    UnassignSourceUseCase,
    {"select_cinema": make_cinema_data()},
)


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
    ("command", "error_type"),
    [
        (IMPORT_LOOKUP, RuntimeError),
        (IMPORT_LOOKUP, ValueError),
        (IMPORT_LOOKUP, SourceNotFoundError),
        (IMPORT, RuntimeError),
        (IMPORT, ValueError),
        (IMPORT, SourceNotFoundError),
        (ASSIGN, RuntimeError),
        (ASSIGN, ValueError),
        (ASSIGN, CinemaSourceAssignmentNotFoundError),
        (UNASSIGN, RuntimeError),
        (UNASSIGN, ValueError),
        (UNASSIGN, SourceNotFoundError),
    ],
    indirect=["command"],
)
def test_unlisted_errors_escape(command: Command, error_type: type[Exception]) -> None:
    """Unexpected application and programming failures keep their traceback."""
    error = error_type("Unexpected failure")
    command.use_case.execute.side_effect = error
    with pytest.raises(error_type) as failure:
        main(command.argv)
    assert failure.value is error
    command.factory.shutdown.assert_awaited_once()
