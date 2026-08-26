"""Cinema update CLI command."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import asdict

import questionary

from marquise import CinemaNotFoundError, MarquiseFactory


def _cinema_choices(
    cinemas: list[dict[str, str | None]],
) -> list[questionary.Choice]:
    """Build cinema choices with an exit option."""
    choices = [
        questionary.Choice(
            title=f"{cinema['name']} — {cinema['address'] or 'No address'}, "
            f"{cinema['city'] or 'No city'}",
            value=cinema,
        )
        for cinema in cinemas
    ]
    choices.append(questionary.Choice(title="← exit", value="__exit__"))
    return choices


async def _select_cinema(factory: MarquiseFactory) -> dict[str, str | None] | None:
    """List cinemas and prompt for one to update."""
    list_cinemas_use_case = factory.list_cinemas_use_case
    response = await list_cinemas_use_case.execute(list_cinemas_use_case.InputData())
    cinemas = [asdict(cinema) for cinema in response.cinemas]
    if not cinemas:
        print("No cinemas available to update.")
        return None

    selected = await questionary.select(
        "Select a cinema to update:", choices=_cinema_choices(cinemas)
    ).ask_async()
    if selected is None or selected == "__exit__":
        print("Cancelled.")
        return None
    return selected


def _field_choices(cinema: dict[str, str | None]) -> list[questionary.Choice]:
    """Build field choices with current values."""
    return [
        questionary.Choice(
            title=f"{field.upper()} [{cinema[field] or 'not set'}]",
            value=field,
        )
        for field in ("name", "address", "city", "website")
    ]


async def _collect_value(field: str, current: str | None) -> str | None:
    """Prompt for one field's replacement value."""
    return await questionary.text(
        f"{field.upper()} (current: {current or 'not set'}):",
        default=current or "",
    ).ask_async()


async def _collect_updates(
    cinema: dict[str, str | None],
) -> dict[str, str | None] | None:
    """Prompt for fields and replacement values."""
    fields = await questionary.checkbox(
        "Which fields would you like to change?",
        choices=_field_choices(cinema),
    ).ask_async()
    if not fields:
        print("No fields selected. Cancelled.")
        return None

    updates: dict[str, str | None] = {}
    for field in fields:
        value = await _collect_value(field, cinema[field])
        if value is None:
            print("Cancelled.")
            return None
        updates[field] = value.strip() or None
    return updates


async def _update_cinema(
    factory: MarquiseFactory,
    cinema_id: str,
    name: str,
    address: str | None,
    city: str | None,
    website: str | None,
) -> dict[str, str | None]:
    """Execute update use case and report expected failures."""
    try:
        update_cinema_use_case = factory.update_cinema_use_case
        response = await update_cinema_use_case.execute(
            update_cinema_use_case.InputData(cinema_id, name, address, city, website)
        )
    except (CinemaNotFoundError, ValueError) as error:
        print(f"Failed to update cinema: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    return asdict(response)


def _print_cinema(cinema: dict[str, str | None]) -> None:
    """Print updated cinema details."""
    print("Cinema updated:")
    print(f"  ID:      {cinema['id']}")
    print(f"  Name:    {cinema['name']}")
    if cinema["address"]:
        print(f"  Address: {cinema['address']}")
    if cinema["city"]:
        print(f"  City:    {cinema['city']}")
    if cinema["website"]:
        print(f"  Website: {cinema['website']}")


async def run_update(factory: MarquiseFactory) -> None:
    """Update an existing cinema after interactive field selection."""
    async with factory:
        cinema = await _select_cinema(factory)
        if cinema is None:
            return
        updates = await _collect_updates(cinema)
        if updates is None:
            return
        _print_cinema(
            await _update_cinema(
                factory,
                cinema["id"] or "",
                updates.get("name", cinema["name"]) or "",
                updates.get("address", cinema["address"]),
                updates.get("city", cinema["city"]),
                updates.get("website", cinema["website"]),
            )
        )


def update() -> None:
    """Update an existing cinema after interactive field selection."""
    asyncio.run(run_update(MarquiseFactory()))
