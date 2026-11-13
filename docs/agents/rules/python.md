# Python rules

Read when writing or reviewing Python in `packages/marquise-core` or `apps/*`.

Types, dataclasses, errors, modules and docstrings follow the Calepin `coding-python` standard ([AGENTS.md](../../../AGENTS.md#shared-coding-standards)). This file holds what only Marquise defines.

## Errors

- Application errors live in `application/exceptions/`, one module per aggregate.
- Repository gateway errors are declared with their protocols under `interface_adapters/repositories/protocols/`.
- The API maps an unvalidated `ValueError` to 422. In `apps/marquise-api/src/marquise_api/exception_handlers.py`, explicitly mapped `ApplicationError` subclasses get their configured status; unmapped ones fall back to 400.

## Tooling

- Run `uv sync` and `uv lock` only from the repo root: one lockfile.

## Quality gate

Run `uv run ruff format .` and `uv run ruff check .` before committing. Commands: [CONTRIBUTING.md](../../../CONTRIBUTING.md#commands).
