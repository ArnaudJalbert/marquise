"""Argparse routing for Marquise CLI commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

from marquise_cli.auth_commands import create_bot, invite, set_role
from marquise_cli.cinema_commands import create, delete, list_cinemas, update
from marquise_cli.import_commands import import_all, import_cinema
from marquise_cli.source_commands import (
    assign,
    list_registered_sources,
    register_sources,
    unassign,
    unregister_sources,
)

Handler = Callable[..., None]

_ROLES = ("member", "editor", "administrator")


def _positive_int(value: str) -> int:
    """Parse an integer greater than zero."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _command(
    commands: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    handler: Handler,
    help_text: str,
    arguments: tuple[str, ...] = (),
) -> argparse.ArgumentParser:
    """Add a command that invokes an existing CLI function."""
    parser = commands.add_parser(name, help=help_text, description=help_text)
    parser.set_defaults(handler=handler, handler_arguments=arguments)
    return parser


def create_parser() -> argparse.ArgumentParser:
    """Create parser for every Marquise CLI command.

    Returns:
        Configured root parser.
    """
    parser = argparse.ArgumentParser(
        prog="marquise",
        description="Manage Marquise movie showtimes.",
    )
    groups = parser.add_subparsers(required=True, title="commands")

    cinema = groups.add_parser("cinema", help="Manage cinemas")
    cinema_commands = cinema.add_subparsers(required=True, title="commands")
    create_command = _command(
        cinema_commands,
        "create",
        create,
        "Create a new cinema.",
        ("name", "address", "city", "website"),
    )
    create_command.add_argument("--name", help="Cinema name")
    create_command.add_argument("--address", help="Cinema street address")
    create_command.add_argument("--city", help="City where cinema is located")
    create_command.add_argument("--website", help="Cinema website URL")
    _command(cinema_commands, "delete", delete, "Delete a cinema.")
    _command(cinema_commands, "update", update, "Update a cinema.")
    list_command = _command(
        cinema_commands,
        "list",
        list_cinemas,
        "List cinemas.",
        ("name", "verbose"),
    )
    list_command.add_argument("--name", "-n", help="Filter cinemas by name")
    list_command.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed cinema information",
    )

    source = groups.add_parser("source", help="Manage showtime sources")
    source_commands = source.add_subparsers(required=True, title="commands")
    _command(
        source_commands,
        "list-registered",
        list_registered_sources,
        "List registered sources.",
    )
    _command(source_commands, "assign", assign, "Assign source to cinema.")
    _command(source_commands, "unassign", unassign, "Unassign source from cinema.")
    _command(source_commands, "register", register_sources, "Register sources.")
    _command(source_commands, "unregister", unregister_sources, "Unregister sources.")

    import_group = groups.add_parser("import", help="Import showtimes")
    import_commands = import_group.add_subparsers(required=True, title="commands")
    _command(
        import_commands,
        "cinema",
        import_cinema,
        "Import showtimes for one cinema.",
    )
    import_command = _command(
        import_commands,
        "all",
        import_all,
        "Import showtimes for every cinema.",
        ("days",),
    )
    import_command.add_argument(
        "--days",
        "-d",
        type=_positive_int,
        default=7,
        help="Days to import, starting today",
    )

    auth = groups.add_parser("auth", help="Manage authenticated accounts")
    auth_commands = auth.add_subparsers(required=True, title="commands")
    invite_command = _command(
        auth_commands,
        "invite",
        invite,
        "Invite a human account.",
        ("email", "role"),
    )
    invite_command.add_argument("email", help="Account email")
    invite_command.add_argument("--role", required=True, choices=_ROLES)

    set_role_command = _command(
        auth_commands,
        "set-role",
        set_role,
        "Set a human account role.",
        ("email", "role"),
    )
    set_role_command.add_argument("email", help="Account email")
    set_role_command.add_argument("--role", required=True, choices=_ROLES)

    create_bot_command = _command(
        auth_commands,
        "create-bot",
        create_bot,
        "Create an Editor Bot and print its refresh token once.",
        ("bot_id",),
    )
    create_bot_command.add_argument("bot_id", help="Immutable Bot Identifier")

    return parser


def dispatch(parser: argparse.ArgumentParser, argv: Sequence[str]) -> int:
    """Parse arguments and invoke selected command.

    Args:
        parser: Configured command parser.
        argv: Command-line arguments excluding program name.

    Returns:
        Command exit code.
    """
    namespace = parser.parse_args(argv)
    arguments = {name: getattr(namespace, name) for name in namespace.handler_arguments}
    namespace.handler(**arguments)
    return 0
