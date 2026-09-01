"""Argparse routing for Marquise CLI commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

from marquise_cli.cinema_commands import create, delete, list_cinemas, update
from marquise_cli.import_commands import import_all, import_cinema
from marquise_cli.role_commands import create as create_role
from marquise_cli.role_commands import list_roles
from marquise_cli.source_commands import (
    assign,
    list_registered_sources,
    register_sources,
    unassign,
    unregister_sources,
)
from marquise_cli.user_commands import (
    create as create_user,
)
from marquise_cli.user_commands import (
    delete as delete_user,
)
from marquise_cli.user_commands import (
    search as search_users,
)
from marquise_cli.user_commands import (
    update as update_user,
)

Handler = Callable[..., None]


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
        cinema_commands, "list", list_cinemas, "List cinemas.", ("name", "verbose")
    )
    list_command.add_argument("--name", "-n", help="Filter cinemas by name")
    list_command.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed cinema information"
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

    role = groups.add_parser("role", help="Manage user roles")
    role_commands = role.add_subparsers(required=True, title="commands")
    create_role_command = _command(
        role_commands,
        "create",
        create_role,
        "Create a role.",
        ("name", "description"),
    )
    create_role_command.add_argument("--name", help="Role slug")
    create_role_command.add_argument("--description", help="Role description")
    _command(role_commands, "list", list_roles, "List roles.")

    user = groups.add_parser("user", help="Manage auth users")
    user_commands = user.add_subparsers(required=True, title="commands")
    create_user_command = _command(
        user_commands,
        "create",
        create_user,
        "Create a user and optionally assign a role.",
        ("email", "password", "role"),
    )
    create_user_command.add_argument("--email", help="User email")
    create_user_command.add_argument("--password", help="User password")
    create_user_command.add_argument("--role", help="Role to assign")
    search_user_command = _command(
        user_commands,
        "search",
        search_users,
        "Search users by email or query.",
        ("email", "query", "verbose"),
    )
    search_user_command.add_argument("--email", help="Exact email match")
    search_user_command.add_argument("--query", "-q", help="Email substring search")
    search_user_command.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show user ID and created timestamp",
    )
    update_user_command = _command(
        user_commands,
        "update",
        update_user,
        "Update a user's email, password, and/or role.",
        ("user_id", "email", "new_email", "password", "role", "clear_role"),
    )
    update_user_command.add_argument("--id", dest="user_id", help="User UUID")
    update_user_command.add_argument("--email", help="Current user email")
    update_user_command.add_argument("--new-email", dest="new_email", help="New email")
    update_user_command.add_argument("--password", help="New password")
    update_user_command.add_argument("--role", help="Role to assign")
    update_user_command.add_argument(
        "--clear-role",
        action="store_true",
        help="Remove the user's role assignment",
    )
    delete_user_command = _command(
        user_commands,
        "delete",
        delete_user,
        "Delete a user.",
        ("user_id", "email"),
    )
    delete_user_command.add_argument("--id", dest="user_id", help="User UUID")
    delete_user_command.add_argument("--email", help="User email")

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
