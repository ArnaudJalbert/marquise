"""Cinema management CLI commands."""

from __future__ import annotations

import asyncio

import questionary
import typer

from marquise import MarquiseFactory

cinema_app = typer.Typer(no_args_is_help=True)


# ── commands ─────────────────────────────────────────────────────────────────


@cinema_app.command()
def create(
    name: str = typer.Option(..., prompt=True, help="Cinema name"),
    address: str | None = typer.Option(None, prompt=True, help="Cinema street address"),
    city: str | None = typer.Option(
        None, prompt=True, help="City where the cinema is located"
    ),
    website: str | None = typer.Option(None, prompt=True, help="Cinema website URL"),
) -> None:
    """Create a new cinema (admin only)."""
    address_val = address if address and address.strip() else None
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
            typer.echo("Cinema created:")
            typer.echo(f"  ID:      {response.id}")
            typer.echo(f"  Name:    {response.name}")
            if response.address:
                typer.echo(f"  Address: {response.address}")
            if response.city:
                typer.echo(f"  City:    {response.city}")
            if response.website:
                typer.echo(f"  Website: {response.website}")
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except Exception as e:
        typer.echo(f"Failed to create cinema: {e}", err=True)
        raise typer.Exit(code=1) from e


@cinema_app.command()
def delete() -> None:
    """Delete a cinema after interactive selection and confirmation (admin only)."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await factory.initialize()
        try:
            response = await factory.cinema.list_cinemas()
        except Exception as e:
            await factory.shutdown()
            typer.echo(f"Failed to list cinemas: {e}", err=True)
            raise typer.Exit(code=1) from e

        if not response.cinemas:
            typer.echo("No cinemas available to delete.")
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
            typer.echo("Cancelled.")
            await factory.shutdown()
            return

        confirmed_name = await questionary.text(
            f'Type "{selected.name}" to confirm deletion:',
        ).ask_async()

        if confirmed_name is None:
            typer.echo("Cancelled.")
            await factory.shutdown()
            return

        if confirmed_name.strip() != selected.name:
            typer.echo(
                f'Name mismatch: expected "{selected.name}", got "{confirmed_name}"',
                err=True,
            )
            await factory.shutdown()
            raise typer.Exit(code=1)

        try:
            await factory.cinema.delete(cinema_id=selected.id)
            typer.echo(f'Cinema "{selected.name}" (ID: {selected.id}) deleted.')
        except Exception as e:
            typer.echo(f"Failed to delete cinema: {e}", err=True)
            raise typer.Exit(code=1) from e
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(f"Failed to delete cinema: {e}", err=True)
        raise typer.Exit(code=1) from e


@cinema_app.command()
def update() -> None:
    """Update an existing cinema after interactive field selection (admin only)."""
    factory = MarquiseFactory()

    async def _run() -> None:
        await factory.initialize()
        try:
            response = await factory.cinema.list_cinemas()
        except Exception as e:
            await factory.shutdown()
            typer.echo(f"Failed to list cinemas: {e}", err=True)
            raise typer.Exit(code=1) from e

        if not response.cinemas:
            typer.echo("No cinemas available to update.")
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
            typer.echo("Cancelled.")
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
            typer.echo("No fields selected. Cancelled.")
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
                typer.echo("Cancelled.")
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
            typer.echo("Cinema updated:")
            typer.echo(f"  ID:      {result.id}")
            typer.echo(f"  Name:    {result.name}")
            if result.address:
                typer.echo(f"  Address: {result.address}")
            if result.city:
                typer.echo(f"  City:    {result.city}")
            if result.website:
                typer.echo(f"  Website: {result.website}")
        except Exception as e:
            typer.echo(f"Failed to update cinema: {e}", err=True)
            raise typer.Exit(code=1) from e
        finally:
            await factory.shutdown()

    try:
        asyncio.run(_run())
    except SystemExit:
        raise
    except Exception as e:
        typer.echo(f"Failed to update cinema: {e}", err=True)
        raise typer.Exit(code=1) from e


@cinema_app.command(name="list")
def list_cinemas(
    name: str | None = typer.Option(
        None, "--name", "-n", help="Filter cinemas by name (case-insensitive)"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed cinema information"
    ),
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
            typer.echo("No cinemas found.")
            return

        typer.echo("Available cinemas:")

        if verbose:
            for c in cinemas:
                parts = [f"ID: {c.id}", f"Name: {c.name}"]
                if c.address:
                    parts.append(f"Address: {c.address}")
                if c.city:
                    parts.append(f"City: {c.city}")
                if c.website:
                    parts.append(f"Website: {c.website}")
                typer.echo(" | ".join(parts))
        else:
            for c in cinemas:
                typer.echo(f"  {c.name}")

    try:
        asyncio.run(_run())
    except Exception as e:
        typer.echo(f"Failed to list cinemas: {e}", err=True)
        raise typer.Exit(code=1) from e
