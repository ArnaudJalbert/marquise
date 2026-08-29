---
type: process
status: active
owner: Aster
review_date: 2026-09-30
---

# Clean Architecture

Canonical architecture guidance for Marquise. The repository’s `AGENTS.md` keeps the short enforced rules; this note holds the detailed rationale and patterns.

## Dependency rule

Dependencies point **inward only**. Outer layers depend on inner layers; inner layers never depend on outer layers.

```text
delivery → infrastructure → interface_adapters → application → domain
```

- **Domain:** entities, value objects, and domain rules. Standard library only; no databases, HTTP, or frameworks.
- **Application:** use cases and repository interfaces. Imports domain only; contains business orchestration, not SQL or HTTP.
- **Interface adapters:** map external data to application/domain shapes through injected collaborators. Never import infrastructure.
- **Infrastructure:** gateways, I/O, and composition-root wiring. Gateways return plain data.
- **Delivery:** thin CLI/API/UI entrypoints. Use configured use cases and the published library facade.

## Boundaries and injection

- Use cases receive repository interfaces; adapters receive gateway protocols; controllers receive use cases.
- Concrete dependencies are built only at the composition root.
- Infrastructure and delivery use input/output DTOs at their edges; domain entities do not leak into delivery signatures.
- Repositories return domain types, not raw dictionaries. Gateways return plain data, not domain entities.
- Domain exceptions are translated by the application layer.
- Read-only projections may use an injected read adapter and application read model instead of constructing domain entities.

## Testability

| Layer | Test | External I/O |
|---|---|---|
| Domain | Unit | None |
| Application | Unit | None; mock repositories |
| Interface adapters | Unit | None; mock injected collaborators |
| Infrastructure | Integration | Real database/network only here |
| Delivery | Unit | None; mock configured use cases |

Everything through interface adapters must be independently testable without external I/O.

## Web boundary

Apps compose shared package exports; packages never depend on apps. UI components receive data and callbacks through props. HTTP belongs in the client package and is injected in tests. Each package builds, lints, typechecks, and tests independently.

## Review gate

Before approval, verify:

- dependency direction remains inward;
- business logic, SQL, and HTTP are in the correct layer;
- collaborators remain injectable;
- delivery uses public facades and DTOs;
- tests prove the changed boundary without live external services;
- no new abstraction or dependency exists without a concrete payoff.

For violations, block the PR. For uncertainty, cite the affected dependency and resolve it with a test, trace, or documented decision.

## Related repository guidance

- [`AGENTS.md`](https://github.com/ArnaudJalbert/marquise/blob/main/AGENTS.md) — short enforced rules.
- [`CONTRIBUTING.md`](https://github.com/ArnaudJalbert/marquise/blob/main/CONTRIBUTING.md) — commands and contribution checks.
- [`Code Review and Constructive Challenge`](Code%20Review%20and%20Constructive%20Challenge.md) — review workflow.
