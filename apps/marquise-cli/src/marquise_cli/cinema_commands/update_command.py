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
from marquise_cli.helpers import connected_factory, print_cinema, select_cinema


def _field_choices(cinema: ListCinemasUseCase.CinemaData) -> list[questionary.Choice]:
    """Build field choices with current values."""
    return [
        questionary.Choice(
            title=f"{field.upper()} [{getattr(cinema, field) or 'not set'}]",
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
    cinema: ListCinemasUseCase.CinemaData,
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
        value = await _collect_value(field, getattr(cinema, field))
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
) -> UpdateCinemaUseCase.OutputData:
    """Execute update use case and report expected failures."""
    try:
        update_cinema_use_case = factory.cinemas.update_cinema_use_case
        response = await update_cinema_use_case.execute(
            update_cinema_use_case.InputData(cinema_id, name, address, city, website)
        )
    except (CinemaNotFoundError, ValueError) as error:
        print(f"Failed to update cinema: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    return response


async def run_update(factory: MarquiseFactory) -> None:
    """Update an existing cinema after interactive field selection."""
    cinema = await select_cinema(factory, "Select a cinema to update:")
    if cinema is None:
        return
    updates = await _collect_updates(cinema)
    if updates is None:
        return
    updated = await _update_cinema(
        factory,
        cinema.id,
        updates.get("name", cinema.name) or "",
        updates.get("address", cinema.address),
        updates.get("city", cinema.city),
        updates.get("website", cinema.website),
    )
    print_cinema("Cinema updated:", updated)


def update() -> None:
    """Update an existing cinema after interactive field selection."""

    async def run() -> None:
        async with connected_factory() as factory:
            await run_update(factory)

    asyncio.run(run())
