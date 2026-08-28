---
type: decision
status: active
owner: Arno
date: 2026-08-28
---

# Decision: Marquise Atlas as Company Knowledge Base

## Context

Marquise needs an organizational source of truth that is distinct from Arno’s personal notes and from GitHub’s engineering records.

## Decision

Create **Marquise Atlas**, a private Obsidian/Git repository, as the company knowledge base.

## Rationale and trade-offs

It creates a discoverable home for current strategic context, operations, decisions, research, and agent definitions while allowing scoped access for future collaborators and Bots. GitHub remains the execution record for software work.

## Consequences

- Company knowledge belongs in Atlas.
- Personal founder thinking remains in Arno’s personal vault.
- Engineering execution remains in `ArnaudJalbert/marquise`.
- Atlas uses lightweight folders, links, and properties rather than duplicated records.
