# Domain docs

## Before exploring

- Read root `CONTEXT-MAP.md`.
- Follow links to every `CONTEXT.md` relevant to current work.
- Read relevant system-wide ADRs under `docs/adr/`.
- Read context-specific ADRs beside each relevant context.

If files do not exist, proceed silently. Create them lazily through the domain-modeling workflow when terminology or decisions need recording.

## Layout

This repo uses multi-context domain documentation:

```text
/
├── CONTEXT-MAP.md
├── CONTEXT.md
├── docs/adr/
├── packages/marquise-core/
│   ├── CONTEXT.md
│   └── docs/adr/
└── web/
    ├── CONTEXT.md
    └── docs/adr/
```

`CONTEXT-MAP.md` is authoritative. It includes shared root vocabulary and links each bounded context. Add or move contexts there as boundaries become clearer.

## Vocabulary

Use terms defined by relevant `CONTEXT.md` files. Avoid synonyms those glossaries reject.

Missing terminology may indicate invented language or a domain-model gap. Reconsider it or record it through the domain-modeling workflow.

## ADR conflicts

Surface contradictions with existing ADRs instead of silently overriding them.
