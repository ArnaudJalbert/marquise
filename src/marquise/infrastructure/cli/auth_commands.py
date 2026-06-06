"""Authentication CLI commands."""

from __future__ import annotations

from typing import Optional

import typer

from marquise.infrastructure.di.container import Container

auth_app = typer.Typer(no_args_is_help=True)


@auth_app.command()
def login(
    email: Optional[str] = typer.Option(None, prompt=True, help="Supabase user email"),
    password: Optional[str] = typer.Option(
        None, prompt=True, hide_input=True, help="Supabase user password"
    ),
) -> None:
    """Authenticate with Supabase and verify admin role."""
    controller = Container().auth_controller
    try:
        session = controller.login(email=email, password=password)
        if session.is_admin:
            typer.echo(f"Logged in as {session.email} (admin)")
        else:
            typer.echo(
                "Logged in but user does not have admin role. "
                "Contact your Supabase project admin to grant access."
            )
    except ValueError as e:
        typer.echo(f"Login failed: {e}", err=True)
        raise typer.Exit(code=1) from e


@auth_app.command()
def logout() -> None:
    """Clear the cached authentication session."""
    controller = Container().auth_controller
    controller.logout()
    typer.echo("Logged out")


@auth_app.command()
def status() -> None:
    """Show current authentication status."""
    controller = Container().auth_controller
    session = controller.status()
    if session is None:
        typer.echo("Not authenticated")
        return
    if session.is_expired:
        typer.echo(f"Session expired (was {session.email})")
        return
    role = "admin" if session.is_admin else "user"
    typer.echo(f"Authenticated as {session.email} ({role})")
