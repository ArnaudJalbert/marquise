# Python coding conventions

Entity, use-case, and package conventions for `packages/marquise-core`.

See also [Atlas Clean Architecture](../atlas/50-processes/Clean%20Architecture.md) for layer rules.

---

## Dataclasses

**Entities** — `@dataclass(kw_only=True, slots=True)`. Validate in `__post_init__`.

**Value objects and use-case InputData** — `@dataclass(frozen=True, slots=True)`.
Validate in `__post_init__`.

**Use-case OutputData** — `@dataclass(frozen=True, slots=True)`.

- Validate **computed or derived** fields (counts, aggregates, transformed values).
- Skip re-validating fields copied from already-validated entities or InputData
  (see CHANGELOG #17).

## Use cases

- `execute(input: InputData) -> OutputData` is the only public method.
- Catch domain exceptions; re-raise as `ApplicationError` subclasses — domain
  exceptions must not escape the application layer.

## Types and style

- Complete type hints everywhere; `str | None` not `Optional[str]`.
- `Any` requires a comment explaining why.
- Google docstrings on every public module, class, method, and function.
- Scenario docstrings on every test function.

## Packages

- `__init__.py`: **re-exports only** — no class or function definitions.
- No module-level mutable state (no global caches or lazy singletons).
- Repositories return domain types, not raw dicts.

## Quality gate

Run Ruff before commit — see [CONTRIBUTING.md](../CONTRIBUTING.md).
