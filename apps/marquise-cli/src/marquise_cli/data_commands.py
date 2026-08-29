"""CLI commands that report screening problems and edit screening metadata."""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from marquise import MarquiseFactory, ReconcileScreeningsCommand


def _parse_corrections(path: str) -> tuple[ReconcileScreeningsCommand.Correction, ...]:
    """Read a JSON list and convert each item to a screening correction."""
    try:
        payload = json.loads(Path(path).read_text())
        if not isinstance(payload, list):
            raise ValueError("correction plan must be a JSON list")
        return tuple(ReconcileScreeningsCommand.Correction(**item) for item in payload)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise SystemExit(f"Invalid correction plan: {error}") from error


async def run_audit(factory: MarquiseFactory) -> None:
    """Check every screening and print the row count and findings as JSON."""
    await factory.initialize()
    try:
        result = await factory.screening_data_audit_query.execute(
            factory.screening_data_audit_query.InputData()
        )
        print(json.dumps(asdict(result), default=datetime.isoformat, indent=2))
    finally:
        await factory.shutdown()


def audit() -> None:
    """Check every screening in the configured database without changing it."""
    asyncio.run(run_audit(MarquiseFactory()))


async def run_reconcile(
    factory: MarquiseFactory, plan: str, apply: bool, confirmation: str | None
) -> None:
    """Read a plan, then preview its corrections or apply one confirmed correction."""
    corrections = _parse_corrections(plan)
    await factory.initialize()
    try:
        try:
            result = await factory.reconcile_screenings_command.execute(
                factory.reconcile_screenings_command.InputData(
                    corrections=corrections, apply=apply, confirmation=confirmation
                )
            )
        except ValueError as error:
            print(str(error), file=sys.stderr)
            raise SystemExit(2) from error
        print(json.dumps(asdict(result), indent=2))
    finally:
        await factory.shutdown()


def reconcile(plan: str, apply: bool = False, confirmation: str | None = None) -> None:
    """Preview a plan; write one correction only with --apply --confirm RECONCILE."""
    asyncio.run(run_reconcile(MarquiseFactory(), plan, apply, confirmation))
