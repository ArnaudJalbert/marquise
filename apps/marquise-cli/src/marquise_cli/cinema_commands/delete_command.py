"""Cinema deletion CLI command."""

from __future__ import annotations

import asyncio
import sys

import questionary

from marquise import CinemaNotFoundError, MarquiseFactory
from marquise_cli.helpers import connected_factory, select_cinema


async def _confirm_deletion(cinema_name: str) -> bool:
    """Confirm deletion by requiring the cinema name."""
    confirmed_name = await questionary.text(
        f'Type "{cinema_name}" to confirm deletion:',
    ).ask_async()

    if confirmed_name is None:
        print("Cancelled.")
        return False

    if confirmed_name.strip() != cinema_name:
        print(
            (f'Name mismatch: expected "{cinema_name}", got "{confirmed_name}"'),
            file=sys.stderr,
        )
        raise SystemExit(1)
    return True


async def _delete_cinema(factory: MarquiseFactory, cinema_id: str) -> None:
    """Delete selected cinema and report failures."""
    try:
        delete_cinema_use_case = factory.cinemas.delete_cinema_use_case
        await delete_cinema_use_case.execute(
            delete_cinema_use_case.InputData(cinema_id=cinema_id)
        )
    except (CinemaNotFoundError, ValueError) as error:
        print(f"Failed to delete cinema: {error}", file=sys.stderr)
        raise SystemExit(1) from error


async def run_delete(factory: MarquiseFactory) -> None:
    """Delete selected cinema after typed-name confirmation."""
    cinema = await select_cinema(factory, "Select a cinema to delete:")
    if cinema is None:
        return
    if not await _confirm_deletion(cinema.name):
        return
    await _delete_cinema(factory, cinema.id)
    print(f'Cinema "{cinema.name}" (ID: {cinema.id}) deleted.')


def delete() -> None:
    """Delete selected cinema after typed-name confirmation.

    Lists cinemas, exits without changes on cancellation, and requires exact
    cinema-name confirmation before deletion.
    """

    async def run() -> None:
        async with connected_factory() as factory:
            await run_delete(factory)

    asyncio.run(run())
