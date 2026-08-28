#!/usr/bin/env python3
"""Run the Hermes sync once per Montreal calendar day at 04:00."""
from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MARKER = Path("/opt/data/state/hermes-sync-last-run")
NOW = datetime.now(ZoneInfo("America/Toronto"))

if NOW.hour != 4:
    raise SystemExit(0)

MARKER.parent.mkdir(parents=True, exist_ok=True)
if MARKER.exists() and MARKER.read_text().strip() == NOW.date().isoformat():
    raise SystemExit(0)

result = subprocess.run(
    ["python3", "scripts/sync-hermes-state.py", "--commit", "--push"],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
if result.returncode != 0:
    print(result.stdout, end="")
    print(result.stderr, end="")
    raise SystemExit(result.returncode)

MARKER.write_text(NOW.date().isoformat() + "\n")
print(result.stdout, end="")
print(f"Ran at {NOW.isoformat()} ({NOW.tzname()})")
