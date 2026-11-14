"""CLI imports preserve logging state and startup configures CLI output."""

from __future__ import annotations

import re
import subprocess
import sys


def test_import_preserves_logging_configuration() -> None:
    """Importing the app leaves the host process's root logger unchanged."""
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import logging\n"
            "root = logging.getLogger()\n"
            "handlers = root.handlers.copy()\n"
            "level = root.level\n"
            "import marquise_cli.app\n"
            "assert root.handlers == handlers\n"
            "assert root.level == level\n",
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def test_startup_logs_info_with_cli_format() -> None:
    """Starting the CLI enables INFO output with the existing timestamp format."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import logging\n"
            "from contextlib import suppress\n"
            "from marquise_cli.app import main\n"
            "with suppress(SystemExit):\n"
            "    main(['--help'])\n"
            "logging.getLogger('cli-test').info('startup message')\n"
            "logging.getLogger('cli-test').debug('hidden debug message')\n",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "usage: marquise" in result.stdout
    assert re.fullmatch(
        r"\d{2}:\d{2}:\d{2} \[INFO\] cli-test: startup message\n", result.stderr
    )
