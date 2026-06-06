"""CLI entry point."""

from __future__ import annotations

import typer

from marquise.infrastructure.cli.auth_commands import auth_app
from marquise.infrastructure.cli.cinema_commands import cinema_app

app = typer.Typer(
    name="marquise",
    help="Marquise — movie showtimes aggregator administration CLI",
    no_args_is_help=True,
)

app.add_typer(auth_app, name="auth", help="Authenticate with Supabase")
app.add_typer(cinema_app, name="cinema", help="Manage cinemas")

if __name__ == "__main__":
    app()
