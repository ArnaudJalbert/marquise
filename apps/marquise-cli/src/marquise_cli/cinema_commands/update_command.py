"""Cinema update CLI command."""

from __future__ import annotations

import asyncio
import sys

import questionary

from marquise import MarquiseFactory


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
