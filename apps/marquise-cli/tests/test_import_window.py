"""Bulk import displays the date window sent to every cinema import."""

from datetime import date
from unittest.mock import MagicMock, call, create_autospec, patch

import pytest

from conftest import FactorySession, make_cinema_data
from marquise import ImportScreeningsCommand, ListCinemasUseCase
from marquise_cli.app import main


@pytest.fixture
def bulk_import_factory(mock_factory: MagicMock) -> MagicMock:
    """Provide two cinemas with successful import results."""
    cinemas = create_autospec(ListCinemasUseCase, instance=True)
    cinemas.execute.return_value = ListCinemasUseCase.OutputData(
        cinemas=[make_cinema_data("cin-1"), make_cinema_data("cin-2")], total=2
    )
    imports = create_autospec(ImportScreeningsCommand, instance=True)
    imports.execute.return_value = ImportScreeningsCommand.OutputData(
        "cin-1", "Test Cinema", "cineplex", (), 0, 0, 0, 0
    )
    mock_factory.cinemas.list_cinemas_use_case = cinemas
    mock_factory.screenings.import_screenings_command = imports
    return mock_factory


def test_import_all_displays_the_imported_window_across_midnight(
    bulk_import_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Midnight cannot shift cinema imports away from the displayed window."""
    with (
        patch(
            "marquise_cli.helpers.create_factory_session",
            FactorySession(bulk_import_factory).open,
        ),
        patch("marquise_cli.import_commands.all_command.date", wraps=date) as clock,
    ):
        clock.today.side_effect = [date(2026, 11, 14), date(2026, 11, 15)]
        assert main(["import", "all", "--days", "3"]) == 0

    assert "Starting bulk import: 2026-11-14 → 2026-11-16 (3 days)" in (
        capsys.readouterr().out
    )
    assert (
        bulk_import_factory.screenings.import_screenings_command.execute.await_args_list
        == [
            call(
                ImportScreeningsCommand.InputData(
                    "cin-1", date(2026, 11, 14), date(2026, 11, 16)
                )
            ),
            call(
                ImportScreeningsCommand.InputData(
                    "cin-2", date(2026, 11, 14), date(2026, 11, 16)
                )
            ),
        ]
    )
