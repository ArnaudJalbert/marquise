---
type: process
status: active
owner: Aster
review_date: 2026-09-30
---

# Hermes Operating Context Snapshot Sync

## Purpose

Preserve a reviewable, non-sensitive trace of Hermes’ operating context for
Marquise without placing live runtime state or credentials in the code
repository.

## Source of truth

- Live Aster identity and memories: the active Hermes home (`$HERMES_HOME`).
- Live Bot identity: the corresponding Hermes profile and `SOUL.md`.
- Versioned audit snapshot: `ops/hermes/` in the Marquise repository, on the
  dedicated `chore/sync-hermes-state` branch.
- Process and decision record: this Atlas note and its related decision note.

The snapshot is an audit trail, not a restorable full Hermes installation.

## Included in the snapshot

- Aster’s `SOUL.md`.
- Persistent `USER.md` and `MEMORY.md`.
- Durable specialist Bot souls, currently Mara’s `SOUL.md`.
- A sanitized Hermes configuration.
- A manifest containing file hashes and source mappings.

## Excluded

Never copy `.env` files, OAuth/auth files, tokens, passwords, session
transcripts, databases, logs, caches, locks, or other runtime credentials.
Sensitive configuration values are replaced with explicit placeholders.

## Procedure

The repository contains the executable procedure at
`scripts/sync-hermes-state.py`.

The script:

1. Requires the dedicated archival branch.
2. Reads the approved non-sensitive Hermes sources.
3. Writes only changed snapshot files and updates `manifest.json`.
4. Can commit and push the branch when invoked with `--commit --push`.
5. Refuses to run on another branch, preventing accidental writes to `main`
   or an unrelated working branch.

Manual invocation:

```bash
python3 scripts/sync-hermes-state.py --commit --push
```

## Automatic cadence

A durable Hermes cron job runs the same commit-and-push procedure daily at
04:00 Montreal time. If no source changed, no new commit is created. The
branch is reviewed or inspected independently and is never merged as part of
the sync job.

## Verification and failure handling

- The script performs a sensitive-pattern scan during setup and maintains
  explicit redactions in `config.sanitized.yaml`.
- Git status, branch, commit, and remote push must be checked before reporting
  a successful sync.
- If the branch is not checked out or the repository has unrelated changes,
  the job must fail rather than overwrite or commit them.
- Any expansion of the included files or automation permissions requires an
  Atlas process update and, when material, a decision record.

## Related records

- [[Decision - Version Hermes operating context on a dedicated branch]]
- [[Knowledge Management Protocol]]
- [[Operating Model]]
