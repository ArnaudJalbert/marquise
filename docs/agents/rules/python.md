# Python rules

Read when writing or reviewing Python in `packages/marquise-core` or `apps/*`.

## Types

- Complete type hints everywhere. Write `str | None`, not `Optional[str]`.
- Use precise types instead of `object` or `TypedDict`. At delivery formatting boundaries, use plain `dict`.
- `Any` needs a comment explaining why.

## Dataclasses

| Kind | Decorator | Validation |
|---|---|---|
| Entity | `@dataclass(kw_only=True, slots=True)` | `__post_init__` |
| Value object, use-case InputData | `@dataclass(frozen=True, slots=True)` | `__post_init__` |
| Use-case OutputData | `@dataclass(frozen=True, slots=True)` | Computed or derived fields only |

OutputData skips re-validating fields copied from already-validated entities or InputData.

## Use cases

- Use case structure follows [use-cases](use-cases/structure.md).
- `InputData` and `OutputData` follow [use-cases](use-cases/input-and-output.md).
- Use-case failure behavior follows [use-cases](use-cases/failure.md).

## Errors

- Entities and value objects raise `ValueError` from `__post_init__` when their values are invalid.
- Application errors subclass `ApplicationError`, with one module per aggregate in `application/exceptions/`.
- Domain exception boundaries follow [architecture](architecture.md#boundaries).
- Repository gateway errors are declared with their protocols under `interface_adapters/repositories/protocols/`.
- The API maps an unvalidated `ValueError` to 422. In `apps/marquise-api/src/marquise_api/exception_handlers.py`, explicitly mapped `ApplicationError` subclasses get their configured status; unmapped ones fall back to 400.

## Modules and packages

- `__init__.py` files only re-export. Definitions live in modules.
- Google docstrings on every public module, class, method and function.

## Tooling

- Python dependencies go through `uv`, never `pip`. Run `uv sync` and `uv lock` only from the repo root: one lockfile.

## Quality gate

Run `uv run ruff format .` and `uv run ruff check .` before committing. Commands: [CONTRIBUTING.md](../../../CONTRIBUTING.md#commands).
