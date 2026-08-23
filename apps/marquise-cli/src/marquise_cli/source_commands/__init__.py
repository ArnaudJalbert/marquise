"""Source management CLI commands."""

__all__ = [
    "assign",
    "list_registered_sources",
    "register_sources",
    "unassign",
    "unregister_sources",
]

from marquise_cli.source_commands.assign_command import assign as assign
from marquise_cli.source_commands.list_registered_command import (
    list_registered_sources as list_registered_sources,
)
from marquise_cli.source_commands.register_command import (
    register_sources as register_sources,
)
from marquise_cli.source_commands.unassign_command import unassign as unassign
from marquise_cli.source_commands.unregister_command import (
    unregister_sources as unregister_sources,
)
