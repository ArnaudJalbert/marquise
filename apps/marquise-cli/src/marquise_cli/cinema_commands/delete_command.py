"""Cinema deletion CLI command."""

from __future__ import annotations

import asyncio
import sys

import questionary

from marquise import CinemaNotFoundError, DeleteCinemaUseCase, MarquiseFactory


async def _select_cinema(factory: MarquiseFactory) -> tuple[str, str] | None:
    """List cinemas and interactively select one for deletion."""
    response = await factory.cinema.list_cinemas()

    if not response.cinemas:
        print("No cinemas available to delete.")
        return None

    choices = [
        questionary.Choice(
            title=f"{c.name} — {c.address or 'No address'}, {c.city or 'No city'}",
            value=c,
        )
        for c in response.cinemas
    ]
    choices.append(questionary.Choice(title="← exit", value="__exit__"))
    selected = await questionary.select(
        "Select a cinema to delete:",
        choices=choices,
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
        await factory.delete_cinema_use_case.execute(
            DeleteCinemaUseCase.InputData(cinema_id=cinema_id)
        )
    except (CinemaNotFoundError, ValueError) as error:
        print(f"Failed to delete cinema: {error}", file=sys.stderr)
        raise SystemExit(1) from error


def delete() -> None:
    """Delete a cinema after interactive selection and confirmation."""
    factory = MarquiseFactory()

    async def _run() -> None:
        async with factory:
            selected = await _select_cinema(factory)
            if selected is None:
                return
            cinema_id, cinema_name = selected
            if not await _confirm_deletion(cinema_name):
                return
            await _delete_cinema(factory, cinema_id)
            print(f'Cinema "{cinema_name}" (ID: {cinema_id}) deleted.')

    asyncio.run(_run())
