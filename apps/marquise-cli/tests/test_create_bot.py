"""Bot provisioning through the CLI command boundary."""

from unittest.mock import create_autospec, patch

import pytest

from marquise import CreateBotUseCase, MarquiseFactory
from marquise_cli.app import main


def test_create_bot_prints_refresh_token_once(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI prints the returned token once after successful provisioning."""
    factory = create_autospec(MarquiseFactory, instance=True)
    use_case = create_autospec(CreateBotUseCase, instance=True)
    use_case.InputData = CreateBotUseCase.InputData
    use_case.execute.return_value = CreateBotUseCase.OutputData(
        "bot-account", "pi.worker_2", "bot-secret"
    )
    factory.create_bot_use_case = use_case
    with (
        patch("marquise_cli.auth_commands.MarquiseFactory", return_value=factory),
        patch(
            "marquise_cli.auth_commands._administrator_credentials",
            return_value=("admin@example.com", "password"),
        ),
    ):
        assert main(["auth", "create-bot", "pi.worker_2"]) == 0
    output = capsys.readouterr()
    assert output.out == "bot-secret\n"
    assert "bot-secret" not in output.err
    use_case.execute.assert_awaited_once_with(
        CreateBotUseCase.InputData("admin@example.com", "password", "pi.worker_2")
    )


def test_bot_creation_failure_prints_no_token(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A failed provisioning attempt exits with a safe error and no token output."""
    from marquise import AuthAdministrationError

    factory = create_autospec(MarquiseFactory, instance=True)
    use_case = create_autospec(CreateBotUseCase, instance=True)
    use_case.InputData = CreateBotUseCase.InputData
    use_case.execute.side_effect = AuthAdministrationError(
        "Unable to assign Bot metadata"
    )
    factory.create_bot_use_case = use_case
    with (
        patch("marquise_cli.auth_commands.MarquiseFactory", return_value=factory),
        patch(
            "marquise_cli.auth_commands._administrator_credentials",
            return_value=("admin@example.com", "password"),
        ),
    ):
        with pytest.raises(SystemExit) as error:
            main(["auth", "create-bot", "pi"])
    assert error.value.code == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "Unable to assign Bot metadata" in output.err
