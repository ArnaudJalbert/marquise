"""Cinema management CLI commands."""

from __future__ import annotations

import asyncio
import sys

import questionary

from marquise import MarquiseFactory

# ── commands ─────────────────────────────────────────────────────────────────


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
        await factory.initialize()
        try:
            response = await factory.cinema.create(
                name=name,
                address=address_val,
                city=city_val,
                website=website_val,
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
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except Exception as e:
        print(f"Failed to create cinema: {e}", file=sys.stderr)
        raise SystemExit(1) from e


def delete() -> None:
    """Delete a cinema after interactive selection and confirmation."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await factory.initialize()
        try:
            response = await factory.cinema.list_cinemas()
        except Exception as e:
            await factory.shutdown()
            print(f"Failed to list cinemas: {e}", file=sys.stderr)
            raise SystemExit(1) from e

        if not response.cinemas:
            print("No cinemas available to delete.")
            await factory.shutdown()
            return

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
            await factory.shutdown()
            return

        confirmed_name = await questionary.text(
            f'Type "{selected.name}" to confirm deletion:',
        ).ask_async()

        if confirmed_name is None:
            print("Cancelled.")
            await factory.shutdown()
            return

        if confirmed_name.strip() != selected.name:
            print(
                f'Name mismatch: expected "{selected.name}", got "{confirmed_name}"',
                file=sys.stderr,
            )
            await factory.shutdown()
            raise SystemExit(1)

        try:
            await factory.cinema.delete(cinema_id=selected.id)
            print(f'Cinema "{selected.name}" (ID: {selected.id}) deleted.')
        except Exception as e:
            print(f"Failed to delete cinema: {e}", file=sys.stderr)
            raise SystemExit(1) from e
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        print(f"Failed to delete cinema: {e}", file=sys.stderr)
        raise SystemExit(1) from e


def update() -> None:
    """Update an existing cinema after interactive field selection."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await factory.initialize()
        try:
            response = await factory.cinema.list_cinemas()
        except Exception as e:
            await factory.shutdown()
            print(f"Failed to list cinemas: {e}", file=sys.stderr)
            raise SystemExit(1) from e

        if not response.cinemas:
            print("No cinemas available to update.")
            await factory.shutdown()
            return

        choices = [
            questionary.Choice(
                title=f"{c.name} — {c.address or 'No address'}, {c.city or 'No city'}",
                value=c,
            )
            for c in response.cinemas
        ]
        choices.append(questionary.Choice(title="← exit", value="__exit__"))

        selected = await questionary.select(
            "Select a cinema to update:",
            choices=choices,
        ).ask_async()

        if selected is None or selected == "__exit__":
            print("Cancelled.")
            await factory.shutdown()
            return

        field_labels = {
            "name": "Name",
            "address": "Address",
            "city": "City",
            "website": "Website",
        }
        selected_fields = await questionary.checkbox(
            "Which fields would you like to change?",
            choices=[
                questionary.Choice(
                    title=f"{label} [{getattr(selected, field) or 'not set'}]",
                    value=field,
                )
                for field, label in field_labels.items()
            ],
        ).ask_async()

        if selected_fields is None or not selected_fields:
            print("No fields selected. Cancelled.")
            await factory.shutdown()
            return

        updates: dict[str, str | None] = {}
        for field in selected_fields:
            label = field_labels[field]
            current = getattr(selected, field) or ""
            new_value = await questionary.text(
                f"{label} (current: {current or 'not set'}):",
                default=current,
            ).ask_async()

            if new_value is None:
                print("Cancelled.")
                await factory.shutdown()
                return

            trimmed = new_value.strip()
            updates[field] = trimmed if trimmed else None

        final_name = updates.get("name", selected.name)
        final_address = updates.get("address", selected.address)
        final_city = updates.get("city", selected.city)
        final_website = updates.get("website", selected.website)

        try:
            result = await factory.cinema.update(
                cinema_id=selected.id,
                name=final_name,
                address=final_address,
                city=final_city,
                website=final_website,
            )
            print("Cinema updated:")
            print(f"  ID:      {result.id}")
            print(f"  Name:    {result.name}")
            if result.address:
                print(f"  Address: {result.address}")
            if result.city:
                print(f"  City:    {result.city}")
            if result.website:
                print(f"  Website: {result.website}")
        except Exception as e:
            print(f"Failed to update cinema: {e}", file=sys.stderr)
            raise SystemExit(1) from e
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        print(f"Failed to update cinema: {e}", file=sys.stderr)
        raise SystemExit(1) from e


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

    try:
        asyncio.run(_run())
    except Exception as e:
        print(f"Failed to list cinemas: {e}", file=sys.stderr)
        raise SystemExit(1) from e
