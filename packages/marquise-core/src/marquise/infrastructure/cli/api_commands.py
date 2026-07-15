"""CLI commands for running the public REST API."""

from __future__ import annotations

import typer

api_app = typer.Typer(no_args_is_help=True)


@api_app.command("serve")
def serve(
    host: str = typer.Option("0.0.0.0", help="Host to bind to."),
    port: int = typer.Option(8000, help="Port to listen on."),
    reload: bool = typer.Option(False, help="Enable auto-reload (dev only)."),
) -> None:
    """Start the read-only public REST API with uvicorn."""
    import uvicorn

    uvicorn.run(
        "marquise.infrastructure.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )
