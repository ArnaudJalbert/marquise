"""Source commands stop on failure without undoing completed work."""

from __future__ import annotations

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
def source_prompts(
    monkeypatch: pytest.MonkeyPatch, source_factory: MagicMock
) -> MagicMock:
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
        sources=_REGISTERED_SOURCES
    )


def test_unregister_empty_source_name_fails_cleanly(
    source_prompts: MagicMock,
    source_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An empty selected source name reports the validation error and exits."""
    _show_registered_sources(source_factory)
    source_prompts.checkbox.return_value.ask_async.return_value = ["", "third"]
    with pytest.raises(SystemExit) as error:
        main(["source", "unregister"])
    assert error.value.code == 1
    assert "Failed: source_name must not be empty" in capsys.readouterr().err
    source_factory.delete_source_use_case.execute.assert_not_awaited()
    source_factory.shutdown.assert_awaited_once()


_REGISTERED_SOURCES = [
    ListSourcesUseCase.SourceData(name=name, display_name=name)
    for name in ("first", "second", "third")
]


@pytest.mark.parametrize(
    ("command", "use_case_attribute", "registered_sources"),
    [
        ("register", "create_source_use_case", []),
        ("unregister", "delete_source_use_case", _REGISTERED_SOURCES),
    ],
)
def test_unexpected_source_error_remains_visible(
    command: str,
    use_case_attribute: str,
    registered_sources: list[ListSourcesUseCase.SourceData],
    source_factory: MagicMock,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unexpected errors propagate unchanged and stop before the next source."""
    source_factory.list_sources_use_case.execute.return_value = (
        ListSourcesUseCase.OutputData(sources=registered_sources)
    )
    operation = getattr(source_factory, use_case_attribute)
    failure = RuntimeError("unexpected failure")
    operation.execute.side_effect = failure
    with pytest.raises(RuntimeError) as error:
        main(["source", command])
    assert error.value is failure
    operation.execute.assert_awaited_once()
    source_factory.shutdown.assert_awaited_once()
    assert "Failed:" not in capsys.readouterr().err
