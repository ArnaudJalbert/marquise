# Testing rules

Read when writing, moving or reviewing tests in either stack.

## Boundary

Everything through interface adapters is unit-testable with zero external I/O. Infrastructure is the only layer that touches real externals. Unit tests stub network calls with injected or patched fetchers where those seams exist. Database gateways use a real disposable database; selected HTTP clients also get offline loopback-HTTP integration tests.

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

Paths are under `packages/marquise-core/tests/` unless stated. Adapter tests are unit tests; there is no `integration_tests/interface_adapters/`.

## Python mechanics

- Function-style tests.
- Every test function has a scenario docstring.
- `@pytest.mark.asyncio` for async tests.
- `create_autospec(Interface, instance=True)` so mocks match real signatures.
- `assert_awaited_once()` and `assert_not_awaited()` for async mocks.
- Run each app suite in its own pytest invocation.

## Transition

Each package has a `tests/new_tests/` folder. All new tests go there, in every package: `packages/marquise-core/tests/new_tests/`, `apps/marquise-api/tests/new_tests/`, `apps/marquise-cli/tests/new_tests/`.

- Old tests stay in place and keep running until their behavior has a test under `new_tests/`.
- Delete old tests in batches, once their behavior is covered by a new test. Do not add new tests to old folders.
- CI runs both folders until the old ones are gone. The core unit step lists `new_tests/` next to `unit_tests/`. The API and CLI steps run their whole `tests/` folder, so they pick up `new_tests/` automatically.
- New tests follow the rules in this file: public interfaces only, `create_autospec` for collaborators, scenario docstrings.

## Coverage

70% minimum for core. Target 100% for `domain/` and `application/`. **Enforced:** `fail_under` in `packages/marquise-core/pyproject.toml` and `--cov-fail-under` in `.github/workflows/quality.yml`.

## Web

- Vitest and Testing Library, colocated as `*.test.ts` or `*.test.tsx`.
- Test behaviour, not implementation.
- Unit tests make no live HTTP calls: inject a mock client or pass data through props.

## Review red flags

- An application-layer test that hits a real database or network.
- A test that needs a live external service to prove application logic.
