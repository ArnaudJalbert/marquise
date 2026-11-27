# Architecture rules

Read when adding a use case, repository, gateway, adapter or endpoint, moving code across layers, wiring dependencies, or changing what delivery apps import.

The layer rules, boundaries, injection and review gate come from the shared `coding-clean-architecture` skill. This file maps them onto Marquise.

## Layers

| Layer | Path |
|---|---|
| Domain | `packages/marquise-core/src/marquise/domain/` |
| Application | `packages/marquise-core/src/marquise/application/` |
| Interface adapters | `packages/marquise-core/src/marquise/interface_adapters/` |
| Infrastructure | `packages/marquise-core/src/marquise/infrastructure/` |
| Composition root | `packages/marquise-core/src/marquise/infrastructure/di/` |
| Delivery | `apps/marquise-api`, `apps/marquise-cli` |

Inside `application/` are `use_cases/` (commands, `*Command`), `queries/` (`*Query`), `repositories/`, `readers/`, and `exceptions/`. `metadata.py` and `movie_workflows.py` hold the metadata contracts ([docs/metadata-contracts.md](../../metadata-contracts.md)).

## Public facade

Apps reach core only through `packages/marquise-core/src/marquise/__init__.py` (`__all__`):

```python
from marquise import create_factory_session

async with create_factory_session() as factory:
    query = factory.cinemas.get_cinema_query
    result = await query.execute(query.InputData(cinema_id="..."))
```

- Apps import only `marquise`, never `marquise.domain`, `marquise.application`, `marquise.interface_adapters` or `marquise.infrastructure`. **Enforced:** `packages/marquise-core/tests/unit_tests/test_import_boundary.py`.
- Changing the facade means updating its snapshot. **Enforced:** `packages/marquise-core/tests/unit_tests/test_public_api.py`.
