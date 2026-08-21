"""Cinema deletion CLI command."""

from __future__ import annotations

import asyncio
import sys

import questionary

from marquise import DeleteCinemaUseCase, MarquiseFactory


def delete() -> None:
    """Delete a cinema after interactive selection and confirmation."""
    factory = MarquiseFactory()

    async def _run() -> None:
        async with factory:
            try:
                response = await factory.cinema.list_cinemas()
            except Exception as e:
                print(f"Failed to list cinemas: {e}", file=sys.stderr)
                raise SystemExit(1) from e

            if not response.cinemas:
                print("No cinemas available to delete.")
                return

            choices = [
                questionary.Choice(
                    title=(
                        f"{c.name} — {c.address or 'No address'}, {c.city or 'No city'}"
                    ),
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
                return

            confirmed_name = await questionary.text(
                f'Type "{selected.name}" to confirm deletion:',
            ).ask_async()

            if confirmed_name is None:
                print("Cancelled.")
                return

            if confirmed_name.strip() != selected.name:
                print(
                    (
                        f'Name mismatch: expected "{selected.name}", '
                        f'got "{confirmed_name}"'
                    ),
                    file=sys.stderr,
                )
                raise SystemExit(1)

            try:
                await factory.delete_cinema_use_case.execute(
                    DeleteCinemaUseCase.InputData(cinema_id=selected.id)
                )
                print(f'Cinema "{selected.name}" (ID: {selected.id}) deleted.')
            except Exception as e:
                print(f"Failed to delete cinema: {e}", file=sys.stderr)
                raise SystemExit(1) from e

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        print(f"Failed to delete cinema: {e}", file=sys.stderr)
        raise SystemExit(1) from e
