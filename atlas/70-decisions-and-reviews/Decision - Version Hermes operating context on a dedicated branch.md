---
type: decision
status: active
owner: Arno
date: 2026-08-28
review_date: 2026-09-30
---

# Decision: Version Hermes operating context on a dedicated branch

## Context

Aster’s identity, persistent memories, Bot souls, and relevant Hermes settings
need a durable, reviewable trace. Hermes runtime data also contains secrets,
credentials, private conversations, and machine-specific state that must not
enter the Marquise repository.

## Decision

Maintain a sanitized snapshot under `ops/hermes/` on the dedicated branch
`chore/sync-hermes-state`. Keep that branch separate from `main` and run the
snapshot process automatically every day at 04:00 Montreal time.

The sync includes Aster’s soul and memories, durable specialist Bot souls,
and sanitized configuration. It excludes secrets and runtime state. The
automation may commit and push the dedicated branch but does not merge it.

## Rationale and trade-offs

This preserves continuity and an audit trail while limiting security and
repository noise. A dedicated branch keeps operational snapshots out of the
production code history, at the cost of requiring separate branch review and
occasional cleanup.

## Consequences

- The live Hermes home remains the runtime source of truth.
- `ops/hermes/` is the versioned audit snapshot.
- Changes are reviewable through Git history without affecting application
  branches.
- Snapshot contents and automation boundaries must remain documented in Atlas.
- The process must fail safely if run from an unexpected branch or unsafe
  repository state.

## Related links

- [[Hermes Operating Context Snapshot Sync]]
- [[Knowledge Management Protocol]]
- [Dedicated snapshot branch](https://github.com/ArnaudJalbert/marquise/tree/chore/sync-hermes-state)
