# Testing rules

Read when writing, moving or reviewing tests in either stack.

## Boundary

Everything through interface adapters is unit-testable with zero external I/O. Infrastructure is the only layer that touches real externals: its gateways get integration tests against a real disposable database, and DI and gateway logic may also get unit tests with fake transports.

| Code | Test location | Swap in |
|---|---|---|
| `domain/` | `unit_tests/domain/` | Nothing |
| `application/` | `unit_tests/application/` | Repository ABCs via `create_autospec` |
| `interface_adapters/` | `unit_tests/interface_adapters/` | Gateway `Protocol`s via `create_autospec` |
| `infrastructure/.../gateways/` | `integration_tests/infrastructure/` | Real disposable database |
| `infrastructure/` DI and gateway logic | `unit_tests/infrastructure/` | Fake transports |
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

## Coverage

70% minimum for core. Target 100% for `domain/` and `application/`. **Enforced:** `fail_under` in `packages/marquise-core/pyproject.toml` and `--cov-fail-under` in `.github/workflows/quality.yml`.

## Web

- Vitest and Testing Library, colocated as `*.test.ts` or `*.test.tsx`.
- Test behaviour, not implementation.
- Unit tests make no live HTTP calls: inject a mock client or pass data through props.

## Review red flags

- An application-layer test that hits a real database or network.
- A test that needs a live external service to prove application logic.
