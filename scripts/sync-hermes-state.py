#!/usr/bin/env python3
"""Sync the non-sensitive Hermes operating context into Marquise."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

HERMES_HOME = Path("/opt/data")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEST = REPO_ROOT / "ops" / "hermes"
EXPECTED_BRANCH = "chore/sync-hermes-state"

FILES = {
    "SOUL.md": HERMES_HOME / "SOUL.md",
    "USER.md": HERMES_HOME / "memories" / "USER.md",
    "MEMORY.md": HERMES_HOME / "memories" / "MEMORY.md",
    "profiles/mara/SOUL.md": HERMES_HOME / "profiles" / "mara" / "SOUL.md",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sanitized_config() -> str:
    source = (HERMES_HOME / "config.yaml").read_text()
    lines = source.splitlines()
    output: list[str] = []
    in_dashboard = False
    redact_continuation = False
    for line in lines:
        if line.startswith("dashboard:"):
            in_dashboard = True
        elif line and not line.startswith(" "):
            in_dashboard = False
            redact_continuation = False
        if redact_continuation and line.startswith(" "):
            continue
        if in_dashboard and "password_hash:" in line:
            output.append("    password_hash: <redacted>")
            redact_continuation = True
        elif line.startswith("TELEGRAM_HOME_CHANNEL:"):
            output.append("TELEGRAM_HOME_CHANNEL: <redacted>")
        else:
            output.append(line)
    return "\n".join(output).rstrip() + "\n"


def run(*args: str, check: bool = True) -> str:
    result = subprocess.run(args, cwd=REPO_ROOT, text=True, capture_output=True, check=check)
    return result.stdout.strip()


def sync() -> bool:
    DEST.mkdir(parents=True, exist_ok=True)
    changed = False
    manifest_files: dict[str, dict[str, object]] = {}
    manifest: dict[str, object] = {
        "description": "Sanitized Hermes operating context snapshot.",
        "excluded": [".env", "auth.json", "state.db", "sessions", "logs", "caches", "locks"],
        "files": manifest_files,
    }

    for relative, source in FILES.items():
        if not source.is_file():
            raise FileNotFoundError(f"Missing Hermes source: {source}")
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        content = source.read_bytes()
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
            changed = True
        manifest_files[relative] = {"sha256": sha256(target), "source": str(source)}

    config_target = DEST / "config.sanitized.yaml"
    config_content = sanitized_config()
    if not config_target.exists() or config_target.read_text() != config_content:
        config_target.write_text(config_content)
        changed = True
    manifest_files["config.sanitized.yaml"] = {
        "sha256": sha256(config_target),
        "source": str(HERMES_HOME / "config.yaml"),
        "redactions": ["dashboard.basic_auth.password_hash", "TELEGRAM_HOME_CHANNEL"],
    }

    manifest_target = DEST / "manifest.json"
    manifest_content = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if not manifest_target.exists() or manifest_target.read_text() != manifest_content:
        manifest_target.write_text(manifest_content)
        changed = True
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    branch = run("git", "branch", "--show-current")
    if branch != EXPECTED_BRANCH:
        raise SystemExit(f"Refusing to sync on branch {branch!r}; expected {EXPECTED_BRANCH!r}.")

    changed = sync()
    print("Hermes snapshot: " + ("updated" if changed else "already current"))
    if args.push and not args.commit:
        raise SystemExit("--push requires --commit")
    if args.commit and changed:
        run("git", "add", "ops/hermes", "scripts/sync-hermes-state.py")
        run("git", "commit", "-m", "chore: sync Hermes operating context")
    if args.push and changed:
        run("git", "push", "-u", "origin", EXPECTED_BRANCH)
    elif args.push:
        run("git", "push", "origin", EXPECTED_BRANCH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
