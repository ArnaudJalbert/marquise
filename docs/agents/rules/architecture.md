# Architecture rules

Read when adding a use case, repository, gateway, adapter or endpoint, moving code across layers, wiring dependencies, or changing what delivery apps import.

## Dependency rule

Dependencies point inward only:

```text
delivery → infrastructure → interface_adapters → application → domain
```

| Layer | Owns | May import |
|---|---|---|
| `domain/` | Entities, value objects, domain rules | Standard library only |
| `application/` | Use cases, repository interfaces (ABCs), business orchestration | `domain` |
| `interface_adapters/` | Mapping external data to application shapes through injected collaborators | `application`, `domain` |
| `infrastructure/` | Gateways, I/O, composition-root wiring (`infrastructure/di/`) | Inner layers |
| `apps/*` (delivery) | Thin CLI and API entrypoints | `marquise` top-level facade only |

Inside `application/` are `use_cases/` (`*UseCase`, plus a few `*Command` import writes), `queries/` (`*Query`), `repositories/`, `readers/`, and `exceptions/`. `metadata.py` and `movie_workflows.py` hold the metadata contracts ([docs/metadata-contracts.md](../../metadata-contracts.md)).

- One responsibility per component.
- SQL and HTTP live in infrastructure gateways. Use cases and repository adapters hold neither.
- Business logic lives in use cases, never in delivery or controllers.

## Boundaries

- Delivery and infrastructure signatures carry InputData and OutputData DTOs. Domain entities stay inside application and domain.
- Repositories return domain types. Gateways return plain data.
- Domain exceptions are translated by the application layer.
- Read-only projections may use an injected read adapter and an application read model instead of building domain entities.
- Gateway contracts consumed by interface adapters are `Protocol`s, so infrastructure implementations are checked structurally. Application repository interfaces stay ABCs.

## Injection

- Use cases receive their dependencies through the constructor, as [use-cases](use-cases.md) defines.
- Adapters receive gateway protocols through the constructor.
- Controllers receive use cases through the constructor.
- Concrete dependencies are built only at the composition root (`infrastructure/di/`).
- State lives in injected objects. Module-level mutable containers, caches and lazy singletons are out.
- Use cases import no DB driver or HTTP client and read no environment variables. Configuration arrives through injected collaborators.

## Public facade

Apps reach core only through `packages/marquise-core/src/marquise/__init__.py` (`__all__`):

```python
from marquise import create_factory, create_factory_session

async with create_factory_session() as factory:
    use_case = factory.get_cinema_use_case
    result = await use_case.execute(use_case.InputData(cinema_id="..."))
```

- Apps import only `marquise`, never `marquise.domain`, `marquise.application`, `marquise.interface_adapters` or `marquise.infrastructure`. **Enforced:** `packages/marquise-core/tests/unit_tests/test_import_boundary.py`.
- Changing the facade means updating its snapshot. **Enforced:** `packages/marquise-core/tests/unit_tests/test_public_api.py`.

## Review gate

Before approving, the reviewer confirms: dependencies still point inward; business logic, SQL and HTTP sit in their layers; collaborators stay injectable; delivery uses the facade and DTOs; tests prove the changed boundary without live services; every new abstraction or dependency has a concrete payoff. A violation blocks the PR. For uncertainty, name the affected dependency and settle it with a test, trace or ADR.
