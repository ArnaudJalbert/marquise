"""Argparse routing for Marquise CLI commands."""

from __future__ import annotations

import argparse
import asyncio
import inspect
from collections.abc import Awaitable, Callable, Sequence

HandlerResult = int | None
Handler = Callable[[argparse.Namespace], HandlerResult | Awaitable[HandlerResult]]

_COMMANDS = (
    ("cinema", "Manage cinemas", ("create", "delete", "update", "list")),
    (
        "source",
        "Manage showtime sources",
        (
            "list-registered",
            "assign",
            "unassign",
            "list-assignments",
            "list-available",
            "register",
            "unregister",
            "import",
        ),
    ),
    ("import", "Bulk import showtimes", ("all",)),
)


def create_parser(fallback_handler: Handler) -> argparse.ArgumentParser:
    """Create parser with fallback routes for unmigrated Typer commands.

    Args:
        fallback_handler: Handler delegated to for every registered command.

    Returns:
        Configured root parser.
    """
    parser = argparse.ArgumentParser(
        prog="marquise",
        description="Marquise movie showtimes aggregator administration CLI",
    )
    groups = parser.add_subparsers(dest="group", required=True)

    for group, help_text, commands in _COMMANDS:
        group_parser = groups.add_parser(group, help=help_text, description=help_text)
        leaves = group_parser.add_subparsers(dest="command", required=True)
        for command in commands:
            leaf = leaves.add_parser(command, add_help=False)
            leaf.set_defaults(handler=fallback_handler, args=[])

    return parser


def dispatch(parser: argparse.ArgumentParser, argv: Sequence[str]) -> int:
    """Parse arguments and invoke selected sync or async command handler.

    Args:
        parser: Configured command parser.
        argv: Command-line arguments excluding program name.

    Returns:
        Command exit code.
    """
    namespace, remaining = parser.parse_known_args(argv)
    namespace.args = remaining
    result = namespace.handler(namespace)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    return result or 0
