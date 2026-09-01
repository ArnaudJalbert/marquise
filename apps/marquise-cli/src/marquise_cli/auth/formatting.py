"""Shared formatting helpers for auth CLI commands."""

from __future__ import annotations

from rich import box
from rich.console import Console
from rich.table import Table

from marquise_cli.auth.store import RoleRecord, UserRecord

_console = Console(markup=False)


def print_users(users: list[UserRecord], *, verbose: bool = False) -> None:
    """Print users in a table."""
    if not users:
        print("No users found.")
        return

    table = Table(
        title="Users",
        box=box.ROUNDED,
        header_style="bold",
        show_lines=True,
    )
    table.add_column("Email", style="cyan")
    table.add_column("Role", style="yellow")
    if verbose:
        table.add_column("ID", style="dim")
        table.add_column("Created", style="green")

    for user in users:
        row: list[str] = [user.email or "-", user.role_name or "-"]
        if verbose:
            row.extend([user.id, user.created_at or "-"])
        table.add_row(*row)

    _console.print(table)


def print_roles(roles: list[RoleRecord]) -> None:
    """Print roles in a table."""
    if not roles:
        print("No roles found.")
        return

    table = Table(
        title="Roles",
        box=box.ROUNDED,
        header_style="bold",
        show_lines=True,
    )
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green", overflow="fold")

    for role in roles:
        table.add_row(role.name, role.description or "-")

    _console.print(table)
