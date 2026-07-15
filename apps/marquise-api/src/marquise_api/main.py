"""Entry point for the marquise-api CLI."""

from __future__ import annotations

import uvicorn


def run() -> None:
    """Start the Marquise API server.

    Installed as the ``marquise-api`` console script.
    """
    uvicorn.run(
        "marquise_api.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
    )
