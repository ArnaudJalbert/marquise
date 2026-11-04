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

- `execute(input_data: InputData) -> OutputData` is the only public method.
- Each use case and query declares its own nested `InputData` and `OutputData` classes and uses them in `execute`. It may inject another use case as a collaborator but never reuses another use case's DTOs. **Enforced:** `packages/marquise-core/tests/unit_tests/application/test_use_case_architecture.py` (its allowlist only shrinks).

## Errors

- Entities, value objects and InputData raise `ValueError` from `__post_init__` on invalid values. The API maps it to 422.
- An InputData that enforces an application limit, not value validity, raises a use-case-specific `ApplicationError` from `application/exceptions/` instead (e.g. `TooManyMovieIdsError` for the 100-id cap in `ListMoviesUseCase`). The API maps each one in `apps/marquise-api/src/marquise_api/exception_handlers.py`.
- Application errors subclass `ApplicationError`, one module per aggregate in `application/exceptions/`.
- Gateway errors live beside their protocols in `interface_adapters/repositories/protocols/` (auth gateway errors in `interface_adapters/exceptions/auth.py`). Adapters translate them into application errors.

## Modules and packages

- `__init__.py` files only re-export. Definitions live in modules.
- Google docstrings on every public module, class, method and function.

## Tooling

- Python dependencies go through `uv`, never `pip`. Run `uv sync` and `uv lock` only from the repo root: one lockfile.

## Quality gate

Run `uv run ruff format .` and `uv run ruff check .` before committing. Commands: [CONTRIBUTING.md](../../../CONTRIBUTING.md#commands).
