"""Cinema update CLI command."""

from __future__ import annotations

import asyncio
import sys

import questionary

from marquise import (
    CinemaNotFoundError,
    ListCinemasUseCase,
    MarquiseFactory,
    UpdateCinemaUseCase,
)

_FIELD_LABELS = {
    "name": "Name",
    "address": "Address",
    "city": "City",
    "website": "Website",
}


async def _select_cinema(
    factory: MarquiseFactory,
) -> ListCinemasUseCase.CinemaData | None:
    """List cinemas and prompt for one to update."""
    response = await factory.cinema.list_cinemas()
    if not response.cinemas:
        print("No cinemas available to update.")
        return None

    choices = [
        questionary.Choice(
            title=f"{cinema.name} — {cinema.address or 'No address'}, "
            f"{cinema.city or 'No city'}",
            value=cinema,
        )
        for cinema in response.cinemas
    ]
    choices.append(questionary.Choice(title="← exit", value="__exit__"))
    selected = await questionary.select(
        "Select a cinema to update:", choices=choices
    ).ask_async()

    if selected is None or selected == "__exit__":
        print("Cancelled.")
        return None
    return selected


async def _collect_updates(
    cinema: ListCinemasUseCase.CinemaData,
) -> dict[str, str | None] | None:
    """Prompt for fields and replacement values."""
    fields = await questionary.checkbox(
        "Which fields would you like to change?",
        choices=[
            questionary.Choice(
                title=f"{label} [{getattr(cinema, field) or 'not set'}]",
                value=field,
            )
            for field, label in _FIELD_LABELS.items()
        ],
    ).ask_async()
    if not fields:
        print("No fields selected. Cancelled.")
        return None

    updates: dict[str, str | None] = {}
    for field in fields:
        current = getattr(cinema, field) or ""
        value = await questionary.text(
            f"{_FIELD_LABELS[field]} (current: {current or 'not set'}):",
            default=current,
        ).ask_async()
        if value is None:
            print("Cancelled.")
            return None
        updates[field] = value.strip() or None
    return updates


async def _update_cinema(
    factory: MarquiseFactory,
    cinema: ListCinemasUseCase.CinemaData,
    updates: dict[str, str | None],
) -> UpdateCinemaUseCase.OutputData:
    """Execute update use case and report expected failures."""
    try:
        return await factory.update_cinema_use_case.execute(
            UpdateCinemaUseCase.InputData(
                cinema_id=cinema.id,
                name=updates.get("name", cinema.name),
                address=updates.get("address", cinema.address),
                city=updates.get("city", cinema.city),
                website=updates.get("website", cinema.website),
            )
        )
    except (CinemaNotFoundError, ValueError) as error:
        print(f"Failed to update cinema: {error}", file=sys.stderr)
        raise SystemExit(1) from error


def _print_cinema(cinema: UpdateCinemaUseCase.OutputData) -> None:
    """Print updated cinema details."""
    print("Cinema updated:")
    print(f"  ID:      {cinema.id}")
    print(f"  Name:    {cinema.name}")
    if cinema.address:
        print(f"  Address: {cinema.address}")
    if cinema.city:
        print(f"  City:    {cinema.city}")
    if cinema.website:
        print(f"  Website: {cinema.website}")


def update() -> None:
    """Update an existing cinema after interactive field selection."""
    factory = MarquiseFactory()

    async def _run() -> None:
        async with factory:
            cinema = await _select_cinema(factory)
            if cinema is None:
                return
            updates = await _collect_updates(cinema)
            if updates is None:
                return
            _print_cinema(await _update_cinema(factory, cinema, updates))

    asyncio.run(_run())
