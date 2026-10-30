"""Tests for the temporary Fly import Machine runner."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def test_runner_propagates_machine_failure_and_destroys_machine(
    tmp_path: Path,
) -> None:
    """A failed import returns its process code and removes its Machine."""
    calls_file = tmp_path / "calls"
    flyctl = tmp_path / "flyctl"
    flyctl.write_text(
        "#!/bin/sh\n"
        'echo "$*" >> "$CALLS_FILE"\n'
        'case "$1" in\n'
        '  machine)\n'
        '    if [ "$2" = run ]; then echo "Machine ID: machine-123"; exit 1; fi\n'
        '    if [ "$2" = status ]; then echo "State: stopped exit_code=23"; fi\n'
        '    if [ "$2" = destroy ]; then exit 0; fi\n'
        '    ;;\n'
        '  logs) echo "import log output" ;;\n'
        'esac\n'
    )
    flyctl.chmod(0o755)
    env = {
        **os.environ,
        "CALLS_FILE": str(calls_file),
        "DAYS": "7",
        "FLY_IMAGE": "registry.fly.io/marquise-db:test",
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
    }

    result = subprocess.run(
        ["bash", "scripts/run_fly_import.sh"],
        check=False,
        capture_output=True,
        env=env,
        text=True,
    )

    assert result.returncode == 23
    assert "import log output" in result.stdout
    calls = calls_file.read_text()
    assert (
        "machine destroy --app marquise-db --force machine-123"
        in calls
    )
    assert "TMDB_API_KEY=" not in calls
