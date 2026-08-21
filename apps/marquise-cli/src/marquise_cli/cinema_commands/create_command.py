"""Cinema creation CLI command."""

from __future__ import annotations

import asyncio
import sys

import questionary

from marquise import CreateCinemaUseCase, MarquiseFactory
from marquise_cli.helpers import select_source


async def _create_cinema(
    factory: MarquiseFactory,
    name: str,
    address: str | None,
    city: str | None,
    website: str | None,
) -> CreateCinemaUseCase.OutputData:
    """Create a cinema and display its details."""
    response = await factory.create_cinema_use_case.execute(
        CreateCinemaUseCase.InputData(
            name=name,
            address=address,
            city=city,
            website=website,
        )
    )
    print("Cinema created:")
    print(f"  ID:      {response.id}")
    print(f"  Name:    {response.name}")
    if response.address:
        print(f"  Address: {response.address}")
    if response.city:
        print(f"  City:    {response.city}")
    if response.website:
        print(f"  Website: {response.website}")
    return response


async def _assign_source(factory: MarquiseFactory, cinema_id: str) -> None:
    """Optionally assign a source to a newly created cinema."""
    if not await questionary.confirm(
        "Assign a showtime source now?",
        default=False,
    ).ask_async():
        return

    source_name = await select_source(factory, "Select a source to assign:")
    if source_name is None:
        return

    assignment = await factory.source.assign_source(
        cinema_id=cinema_id,
        source_name=source_name,
    )
    print("Source assigned:")
    print(f"  Cinema:      {assignment.cinema_id}")
    print(f"  Source:      {assignment.source_name}")


def create(
    name: str | None = None,
    address: str | None = None,
    city: str | None = None,
    website: str | None = None,
) -> None:
    """Create a new cinema."""
    name = name or input("Cinema name: ")
    address = address if address is not None else input("Cinema street address: ")
    city = city if city is not None else input("City where cinema is located: ")
    website = website if website is not None else input("Cinema website URL: ")
    address_val = address if address.strip() else None
    city_val = city if city and city.strip() else None
    website_val = website if website and website.strip() else None

    factory = MarquiseFactory()

    async def _run() -> None:
        async with factory:
            response = await _create_cinema(
                factory,
                name=name,
                address=address_val,
                city=city_val,
                website=website_val,
            )
            try:
                await _assign_source(factory, response.id)
            except Exception as e:
                print(f"Failed to assign source: {e}", file=sys.stderr)
                raise SystemExit(1) from e

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        print(f"Failed to create cinema: {e}", file=sys.stderr)
        raise SystemExit(1) from e
