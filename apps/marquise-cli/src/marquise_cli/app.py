"""CLI entry point."""

from __future__ import annotations

import logging

import typer

from marquise_cli.cinema_commands import cinema_app
from marquise_cli.import_commands import import_app
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

if __name__ == "__main__":
    app()
