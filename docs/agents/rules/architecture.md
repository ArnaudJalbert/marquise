# Architecture rules

Read when adding or moving Python code across layers, wiring dependencies, or changing what delivery apps import.

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

- Use cases receive repository interfaces through the constructor.
- Adapters receive gateway protocols through the constructor.
- Controllers receive use cases through the constructor.
- Concrete dependencies are built only at the composition root (`infrastructure/di/`).
- State lives in injected objects. Module-level mutable containers, caches and lazy singletons are out.
- Use cases read configuration through injected collaborators, never from environment variables, DB drivers or HTTP clients.

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

## Lean inside the architecture

Ponytail applies after these rules hold. When the smallest change would skip a layer, merge boundaries, hard-code a dependency or expose domain types at the edge, find a smaller change that keeps the architecture. Add an abstraction or dependency only with a concrete payoff.
