"""Source commands stop on failure without undoing completed work."""

from __future__ import annotations

from functools import partial
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest

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
    mock_factory.create_source_use_case = create_autospec(
        CreateSourceUseCase, instance=True
    )
    mock_factory.create_source_use_case.InputData = CreateSourceUseCase.InputData
    mock_factory.delete_source_use_case = create_autospec(
        DeleteSourceUseCase, instance=True
    )
    mock_factory.delete_source_use_case.InputData = DeleteSourceUseCase.InputData
    return mock_factory


@pytest.fixture(autouse=True)
def source_prompts(monkeypatch: pytest.MonkeyPatch, source_factory: MagicMock) -> None:
    """Use deterministic prompt answers and replace only the factory boundary."""
    monkeypatch.setattr(register_command, "MarquiseFactory", lambda: source_factory)
    monkeypatch.setattr(unregister_command, "MarquiseFactory", lambda: source_factory)
    questionary = create_autospec(register_command.questionary)
    questionary.text.return_value.ask_async = AsyncMock(return_value="Source details")
    questionary.checkbox.return_value.ask_async = AsyncMock(
        return_value=["first", "second", "third"]
    )
    questionary.confirm.return_value.ask_async = AsyncMock(return_value=True)
    monkeypatch.setattr(register_command, "questionary", questionary)
    monkeypatch.setattr(unregister_command, "questionary", questionary)


def test_register_preserves_success_and_rerun_finishes(
    source_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failed registration leaves earlier sources registered and rerun skips them."""
    creation = source_factory.create_source_use_case
    creation.execute.side_effect = partial(_register_until_second, source_factory)
    with pytest.raises(SystemExit) as error:
        main(["source", "register"])
    assert error.value.code == 1
    output = capsys.readouterr()
    assert "Created: first" in output.out
    assert "second already exists" in output.err
    assert "--- Registering: third ---" not in output.out
    assert [call.args[0].name for call in creation.execute.await_args_list] == [
        "first",
        "second",
    ]
    source_factory.shutdown.assert_awaited_once()
    _finish_registration(source_factory)
    output = capsys.readouterr().out
    assert "--- Registering: first ---" not in output
    assert "Created: second" in output
    assert "Created: third" in output


def _register_until_second(
    factory: MagicMock, request: CreateSourceUseCase.InputData
) -> CreateSourceUseCase.OutputData:
    """Keep successful writes while failing on the second source."""
    if request.name == "second":
        raise SourceAlreadyExistsError("second already exists")
    return _persist_source(factory, request)


def _persist_source(
    factory: MagicMock, request: CreateSourceUseCase.InputData
) -> CreateSourceUseCase.OutputData:
    """Keep source state at the stubbed application boundary across runs."""
    factory.list_sources_use_case.execute.return_value.sources.append(
        ListSourcesUseCase.SourceData(
            name=request.name, display_name=request.display_name
        )
    )
    return CreateSourceUseCase.OutputData(
        name=request.name, display_name=request.display_name
    )


def _finish_registration(factory: MagicMock) -> None:
    """Retry with the same source state after resolving the failure."""
    creation = factory.create_source_use_case
    creation.execute.reset_mock(side_effect=True)
    creation.execute.side_effect = partial(_persist_source, factory)
    assert main(["source", "register"]) == 0
    assert [call.args[0].name for call in creation.execute.await_args_list] == [
        "second",
        "third",
    ]


def test_unregister_missing_source_stops_remaining_deletions(
    source_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing second source exits non-zero before removing the third."""
    _show_registered_sources(source_factory)
    deletion = source_factory.delete_source_use_case
    deletion.execute.side_effect = [
        None,
        SourceNotFoundError("second was not found"),
        None,
    ]
    with pytest.raises(SystemExit) as error:
        main(["source", "unregister"])
    assert error.value.code == 1
    output = capsys.readouterr()
    assert "Removed: first" in output.out
    assert "second was not found" in output.err
    assert "Removed: third" not in output.out
    assert [call.args[0].source_name for call in deletion.execute.await_args_list] == [
        "first",
        "second",
    ]
    source_factory.shutdown.assert_awaited_once()


def _show_registered_sources(factory: MagicMock) -> None:
    """List all three sources for removal."""
    factory.list_sources_use_case.execute.return_value = ListSourcesUseCase.OutputData(
        sources=[
            ListSourcesUseCase.SourceData(name=name, display_name=name)
            for name in ("first", "second", "third")
        ]
    )


@pytest.mark.parametrize("command", ["register", "unregister"])
def test_unexpected_source_error_remains_visible(
    command: str, source_factory: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unexpected errors propagate unchanged and stop before the next source."""
    _show_registered_sources(source_factory)
    if command == "register":
        source_factory.list_sources_use_case.execute.return_value = (
            ListSourcesUseCase.OutputData(sources=[])
        )
    operation = (
        source_factory.create_source_use_case
        if command == "register"
        else source_factory.delete_source_use_case
    )
    failure = ValueError("unexpected failure")
    operation.execute.side_effect = failure
    with pytest.raises(ValueError) as error:
        main(["source", command])
    assert error.value is failure
    operation.execute.assert_awaited_once()
    source_factory.shutdown.assert_awaited_once()
    assert "Failed:" not in capsys.readouterr().err
