"""CLI entry point."""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence

from marquise_cli.routing import create_parser, dispatch


def main(argv: Sequence[str] | None = None) -> int:
    """Run Marquise CLI.

    Args:
        argv: Command-line arguments excluding program name. Uses process arguments
            when omitted.

    Returns:
        Process exit code.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return dispatch(create_parser(), sys.argv[1:] if argv is None else argv)


if __name__ == "__main__":
    raise SystemExit(main())
