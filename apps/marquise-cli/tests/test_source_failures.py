"""Source commands stop on failure without undoing completed work."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

from conftest import factory_session, mock_use_case
from marquise import (
    CreateSourceUseCase,
    DeleteSourceUseCase,
    ListRegistrySourcesUseCase,
    ListSourcesUseCase,
    SourceAlreadyExistsError,
    SourceNotFoundError,
)
from marquise_cli.app import main
from marquise_cli.source_commands import register_command, unregister_command


@pytest.fixture
def source_factory(mock_factory: MagicMock) -> MagicMock:
    """Provide three available sources and autospecced source operations."""
    registry = create_autospec(ListRegistrySourcesUseCase, instance=True)
    registry.execute.return_value = ListRegistrySourcesUseCase.OutputData(
        sources=[
            ListRegistrySourcesUseCase.SourceEntry(name=name)
            for name in ("first", "second", "third")
        ]
    )
    listing = create_autospec(ListSourcesUseCase, instance=True)
    listing.execute.return_value = ListSourcesUseCase.OutputData(sources=[])
    mock_factory.list_registry_sources_use_case = registry
    mock_factory.list_sources_use_case = listing
    mock_factory.create_source_use_case = mock_use_case(CreateSourceUseCase)
    mock_factory.delete_source_use_case = mock_use_case(DeleteSourceUseCase)
    return mock_factory


@pytest.fixture(autouse=True)
def source_prompts(
    monkeypatch: pytest.MonkeyPatch, source_factory: MagicMock
) -> MagicMock:
    """Use deterministic prompt answers and replace only the factory boundary."""
    monkeypatch.setattr(
        "marquise_cli.helpers.create_factory_session", factory_session(source_factory)
    )
    questionary = create_autospec(register_command.questionary)
    questionary.text.return_value.ask_async = AsyncMock(return_value="Source details")
    questionary.checkbox.return_value.ask_async = AsyncMock(
        return_value=["first", "second", "third"]
    )
    questionary.confirm.return_value.ask_async = AsyncMock(return_value=True)
    monkeypatch.setattr(register_command, "questionary", questionary)
    monkeypatch.setattr(unregister_command, "questionary", questionary)
    return questionary


def test_register_existing_source_stops_remaining_registrations(
    source_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """A duplicate second source exits non-zero before registering the third."""
    creation = source_factory.create_source_use_case
    creation.execute.side_effect = [
        CreateSourceUseCase.OutputData(name="first", display_name="First"),
        SourceAlreadyExistsError("second already exists"),
        CreateSourceUseCase.OutputData(name="third", display_name="Third"),
    ]
    _assert_stopped_after_second(source_factory, "register", "name")
    output = capsys.readouterr()
    assert "Created: first" in output.out
    assert "second already exists" in output.err
    assert "--- Registering: third ---" not in output.out


def test_register_empty_display_name_fails_cleanly(
    source_prompts: MagicMock,
    source_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An empty display name reports the validation error and exits non-zero."""
    source_prompts.text.return_value.ask_async.return_value = ""
    with pytest.raises(SystemExit) as error:
        main(["source", "register"])
    assert error.value.code == 1
    assert "Failed: display_name must not be empty" in capsys.readouterr().err
    source_factory.create_source_use_case.execute.assert_not_awaited()
    source_factory.shutdown.assert_awaited_once()


def test_unregister_missing_source_stops_remaining_deletions(
    source_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing second source exits non-zero before removing the third."""
    _show_sources(source_factory, _REGISTERED_SOURCES)
    source_factory.delete_source_use_case.execute.side_effect = [
        None,
        SourceNotFoundError("second was not found"),
        None,
    ]
    _assert_stopped_after_second(source_factory, "unregister", "source_name")
    output = capsys.readouterr()
    assert "Removed: first" in output.out
    assert "second was not found" in output.err
    assert "Removed: third" not in output.out


def _assert_stopped_after_second(
    factory: MagicMock, command: str, name_field: str
) -> None:
    """Run a source command and check it stopped after the second source."""
    operation = getattr(factory, _OPERATION_BY_COMMAND[command])
    with pytest.raises(SystemExit) as error:
        main(["source", command])
    assert error.value.code == 1
    attempted = operation.execute.await_args_list
    assert [getattr(call.args[0], name_field) for call in attempted] == [
        "first",
        "second",
    ]
    factory.shutdown.assert_awaited_once()


def _show_sources(
    factory: MagicMock, sources: list[ListSourcesUseCase.SourceData]
) -> None:
    """List the given sources as already registered."""
    factory.list_sources_use_case.execute.return_value = ListSourcesUseCase.OutputData(
        sources=sources
    )


_REGISTERED_SOURCES = [
    ListSourcesUseCase.SourceData(name=name, display_name=name)
    for name in ("first", "second", "third")
]

_OPERATION_BY_COMMAND = {
    "register": "create_source_use_case",
    "unregister": "delete_source_use_case",
}


@dataclass(frozen=True, slots=True)
class SourceErrorCase:
    """Configure a source command, its registered sources and its failure."""

    command: str
    registered_sources: list[ListSourcesUseCase.SourceData]
    failure: Exception


@pytest.mark.parametrize(
    "case",
    [
        SourceErrorCase("register", [], RuntimeError("unexpected failure")),
        SourceErrorCase("register", [], ValueError("unexpected value")),
        SourceErrorCase(
            "unregister", _REGISTERED_SOURCES, RuntimeError("unexpected failure")
        ),
    ],
    ids=["register", "register-value-error", "unregister"],
)
def test_unexpected_source_error_remains_visible(
    case: SourceErrorCase,
    source_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unexpected errors propagate unchanged and stop before the next source."""
    _show_sources(source_factory, case.registered_sources)
    operation = getattr(source_factory, _OPERATION_BY_COMMAND[case.command])
    operation.execute.side_effect = case.failure
    with pytest.raises(type(case.failure)) as error:
        main(["source", case.command])
    assert error.value is case.failure
    operation.execute.assert_awaited_once()
    source_factory.shutdown.assert_awaited_once()
    assert "Failed:" not in capsys.readouterr().err
