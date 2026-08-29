---
type: decision
status: active
owner: Arno
date: 2026-08-29
review_date: 2026-09-30
---

# Decision: Establish Orson as Staff Engineer and Architecture Lead

## Context

Marquise has Mara as a specialist for showtime data reliability. The product also needs continuous technical stewardship across the codebase: architecture, design review, implementation quality, and safe delivery.

## Decision

Establish **Orson** as Marquise’s Staff Engineer and Architecture Lead. He is the primary implementation partner for assigned work and performs the technical review of every non-draft PR before Arno’s final review.

## Rationale and trade-offs

The role combines Tech Lead execution with architecture stewardship. It is intentionally not a broad autonomous CTO role: product priorities, major technical bets, merge, deployment, and irreversible actions remain with Arno. The initial manual review process favors a reliable standard over premature automation.

## Consequences

- PRs gain an independent technical gate before Arno reviews them.
- Orson partners with Mara to turn validated data issues into safe systemic fixes.
- Architecture decisions and review procedure become durable Atlas artifacts.
- The role must be reviewed after 30 days for value, bottleneck risk, and scope fit.

## Related links

- [[../40-agents/Orson — Staff Engineer and Architecture Lead]]
- [[../50-processes/Technical Review by Orson]]
- [[../80-research/Staff Engineer and Architecture Lead Role]]
