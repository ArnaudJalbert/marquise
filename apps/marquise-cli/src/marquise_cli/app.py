"""CLI entry point and temporary Typer fallback."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence

import typer

from marquise_cli.cinema_commands import cinema_app
from marquise_cli.import_commands import import_app
from marquise_cli.routing import create_parser, dispatch
from marquise_cli.source_commands import source_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = typer.Typer(
    name="marquise",
    help="Marquise — movie showtimes aggregator administration CLI",
    no_args_is_help=True,
)
app.add_typer(cinema_app, name="cinema", help="Manage cinemas")
app.add_typer(source_app, name="source", help="Manage showtime sources")
app.add_typer(import_app, name="import", help="Bulk import showtimes")


def _run_typer(namespace: argparse.Namespace) -> int:
    """Delegate an unmigrated command to Typer.

    Args:
        namespace: Parsed group, command, and remaining arguments.

    Returns:
        Zero when Typer returns normally.
    """
    app(args=[namespace.group, namespace.command, *namespace.args])
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run Marquise CLI through argparse routing.

    Args:
        argv: Command-line arguments excluding program name. Uses process arguments
            when omitted.

    Returns:
        Process exit code.
    """
    return dispatch(create_parser(_run_typer), sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
