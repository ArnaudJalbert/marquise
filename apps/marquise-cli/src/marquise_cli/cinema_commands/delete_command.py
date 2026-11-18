"""Cinema deletion CLI command."""

from __future__ import annotations

import asyncio
import sys

import questionary

from marquise import (
    CinemaNotFoundError,
    ListCinemasUseCase,
    MarquiseFactory,
)
from marquise_cli.helpers import list_every_cinema, run_with_factory


def _cinema_choices(
    cinemas: list[ListCinemasUseCase.CinemaData],
) -> list[questionary.Choice]:
    """Build deletion choices with an exit option."""
    choices = [
        questionary.Choice(
            title=f"{cinema.name} — {cinema.address or 'No address'}, "
            f"{cinema.city or 'No city'}",
            value=cinema,
        )
        for cinema in cinemas
    ]
    choices.append(questionary.Choice(title="← exit", value="__exit__"))
    return choices


async def _select_cinema(factory: MarquiseFactory) -> tuple[str, str] | None:
    """List cinemas and interactively select one for deletion."""
    cinemas = await list_every_cinema(factory, name=None)

    if not cinemas:
        print("No cinemas available to delete.")
        return None

    selected = await questionary.select(
        "Select a cinema to delete:",
        choices=_cinema_choices(cinemas),
    ).ask_async()

    if selected is None or selected == "__exit__":
        print("Cancelled.")
        return None
    return selected.id, selected.name


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
    selected = await _select_cinema(factory)
    if selected is None:
        return
    cinema_id, cinema_name = selected
    if not await _confirm_deletion(cinema_name):
        return
    await _delete_cinema(factory, cinema_id)
    print(f'Cinema "{cinema_name}" (ID: {cinema_id}) deleted.')


def delete() -> None:
    """Delete selected cinema after typed-name confirmation.

    Lists cinemas, exits without changes on cancellation, and requires exact
    cinema-name confirmation before deletion.
    """
    asyncio.run(run_with_factory(run_delete))
