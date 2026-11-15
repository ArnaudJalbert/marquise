# Testing rules

Read when writing, moving or reviewing tests in either stack.

The test boundary, Python mechanics, web testing and review red flags follow the shared `coding-testing` skill, and use-case tests follow `coding-use-cases`. This file holds what only Marquise defines.

## Boundary

| Code | Test location | Swap in |
|---|---|---|
| `domain/` | `unit_tests/domain/` | Nothing |
| `application/` | `unit_tests/application/` | Repository ABCs via `create_autospec` |
| `interface_adapters/` | `unit_tests/interface_adapters/` | Gateway `Protocol`s via `create_autospec` |
| `infrastructure/supabase/gateways/` | `integration_tests/infrastructure/supabase/` | Real disposable database |
| `infrastructure/` unit coverage | `unit_tests/infrastructure/` | Fakes, fixtures or stubbed fetchers |
| Selected `infrastructure/sources/` HTTP clients | `integration_tests/infrastructure/sources/` | Loopback HTTP server |
| `apps/marquise-api/` | `apps/marquise-api/tests/` | `MarquiseFactory` |
| `apps/marquise-cli/` | `apps/marquise-cli/tests/` | `MarquiseFactory` |

Paths are under `packages/marquise-core/tests/` unless a row names root `integration_tests/`. Adapter tests are unit tests; there is no `integration_tests/interface_adapters/`.

## Python mechanics

- Run each app suite in its own pytest invocation.
- New tests follow `coding-testing`.

## Temporary pruning exception

For [#564](https://github.com/ArnaudJalbert/marquise/issues/564)'s pruning children #566 through #571 only, the replacement-coverage prerequisite above is waived. These tickets prune tests for domain objects, DTOs and exceptions, application workflows, factories and resource lifecycle, sources and providers, persistence, API and CLI. This exception ends when those tickets finish and does not apply to #572 or other work.

- Prune existing suites in place. Existing tests may be edited when that reduces test count while preserving useful coverage.
- Delete duplicates only when named surviving tests cover the same useful behavior, regardless of folder. Checks that exercise only configured mocks or language machinery may be deleted without replacement when they protect no Marquise behavior or explicit contract.
- Preserve unique assertions, including useful private-method coverage, test discovery, architecture and public API checks, and existing coverage gates.
- Add no new tests during this phase. New tests and substantial rewrites belong to the later code refactors.

## Coverage

70% minimum for core. Target 100% for `domain/` and `application/`. **Enforced:** `fail_under` in `packages/marquise-core/pyproject.toml` and `--cov-fail-under` in `.github/workflows/quality.yml`.
