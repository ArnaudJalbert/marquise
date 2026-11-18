"""Cinema creation CLI command."""

from __future__ import annotations

import asyncio
import sys

import questionary

from marquise import (
    CinemaAlreadyExistsError,
    CinemaIdAlreadyExistsError,
    CinemaNotFoundError,
    CinemaSourceAssignmentAlreadyExistsError,
    CreateCinemaUseCase,
    MarquiseFactory,
    SourceNotFoundError,
)
from marquise_cli.helpers import connected_factory, print_cinema, select_source


async def _create_cinema(
    factory: MarquiseFactory,
    name: str,
    address: str | None,
    city: str | None,
    website: str | None,
) -> CreateCinemaUseCase.OutputData:
    """Create a cinema and display its details."""
    try:
        create_cinema_use_case = factory.create_cinema_use_case
        response = await create_cinema_use_case.execute(
            create_cinema_use_case.InputData(
                name=name,
                address=address,
                city=city,
                website=website,
            )
        )
    except (CinemaAlreadyExistsError, CinemaIdAlreadyExistsError, ValueError) as error:
        print(f"There was an error when creating the cinema: {error}", file=sys.stderr)
        raise SystemExit(1) from error

    print_cinema("Cinema created:", response)
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

    try:
        assign_source_use_case = factory.assign_source_use_case
        assignment = await assign_source_use_case.execute(
            assign_source_use_case.InputData(
                cinema_id=cinema_id,
                source_name=source_name,
            )
        )
    except (
        CinemaNotFoundError,
        CinemaSourceAssignmentAlreadyExistsError,
        SourceNotFoundError,
        ValueError,
    ) as error:
        print(
            f"There was an error when assigning the source to the cinema: {error}",
            file=sys.stderr,
        )
        raise SystemExit(1) from error
    print("Source assigned:")
    print(f"  Cinema:      {assignment.cinema_id}")
    print(f"  Source:      {assignment.source_name}")


async def run_create(
    factory: MarquiseFactory,
    *,
    name: str,
    address: str | None,
    city: str | None,
    website: str | None,
) -> None:
    """Create a cinema and optionally assign a source."""
    cinema = await _create_cinema(
        factory,
        name=name,
        address=address,
        city=city,
        website=website,
    )
    await _assign_source(factory, cinema.id)


def create(
    name: str | None = None,
    address: str | None = None,
    city: str | None = None,
    website: str | None = None,
) -> None:
    """Create a cinema from arguments or interactive prompts.

    Args:
        name: Cinema name, prompted when omitted.
        address: Cinema street address, prompted when omitted.
        city: Cinema city, prompted when omitted.
        website: Cinema website URL, prompted when omitted.
    """
    name = name or input("Cinema name: ")
    address = address if address is not None else input("Cinema street address: ")
    city = city if city is not None else input("City where cinema is located: ")
    website = website if website is not None else input("Cinema website URL: ")
    address_val = address if address.strip() else None
    city_val = city if city and city.strip() else None
    website_val = website if website and website.strip() else None

    async def run() -> None:
        async with connected_factory() as factory:
            await run_create(
                factory,
                name=name,
                address=address_val,
                city=city_val,
                website=website_val,
            )

    asyncio.run(run())
