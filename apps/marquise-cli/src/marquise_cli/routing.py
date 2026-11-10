"""Argparse routing for Marquise CLI commands."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence

from marquise_cli.cinema_commands import create, delete, list_cinemas, update
from marquise_cli.import_commands import import_all, import_cinema
from marquise_cli.metadata_commands import merge_apply, merge_preview, refresh
from marquise_cli.source_commands import (
    assign,
    list_registered_sources,
    register_sources,
    unassign,
    unregister_sources,
)

Handler = Callable[..., int | None]


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

    movie = groups.add_parser("movie", help="Manage movie metadata")
    movie_commands = movie.add_subparsers(required=True, title="commands")
    refresh_command = _command(
        movie_commands,
        "refresh",
        refresh,
        "Refresh movie metadata.",
        ("movie_id", "all_movies"),
    )
    target = refresh_command.add_mutually_exclusive_group(required=True)
    target.add_argument("--movie-id")
    target.add_argument("--all", action="store_true", dest="all_movies")
    preview = _command(
        movie_commands,
        "merge-preview",
        merge_preview,
        "Preview a guarded merge.",
        ("survivor_id", "duplicate_ids"),
    )
    preview.add_argument("survivor_id")
    preview.add_argument("duplicate_ids", nargs="+")
    apply = _command(
        movie_commands,
        "merge-apply",
        merge_apply,
        "Apply an approved merge preview.",
        ("survivor_id", "duplicate_ids", "preview_file"),
    )
    apply.add_argument("survivor_id")
    apply.add_argument("duplicate_ids", nargs="+")
    apply.add_argument("--preview-file", required=True)

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
    result = namespace.handler(**arguments)
    return result if isinstance(result, int) else 0
