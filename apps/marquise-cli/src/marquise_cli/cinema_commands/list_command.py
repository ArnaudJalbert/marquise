"""Cinema listing CLI command."""

from __future__ import annotations

import asyncio

from marquise import MarquiseFactory


def list_cinemas(
    name: str | None = None,
    verbose: bool = False,
) -> None:
    """List all available cinemas."""

    factory = MarquiseFactory()

    async def _run() -> None:
        await factory.initialize()
        try:
            response = await factory.cinema.list(name=name)
        finally:
            await factory.shutdown()

        cinemas = response.cinemas

        if not cinemas:
            print("No cinemas found.")
            return

        print("Available cinemas:")

        if verbose:
            for c in cinemas:
                parts = [f"ID: {c.id}", f"Name: {c.name}"]
                if c.address:
                    parts.append(f"Address: {c.address}")
                if c.city:
                    parts.append(f"City: {c.city}")
                if c.website:
                    parts.append(f"Website: {c.website}")
                print(" | ".join(parts))
        else:
            for c in cinemas:
                print(f"  {c.name}")

    asyncio.run(_run())
