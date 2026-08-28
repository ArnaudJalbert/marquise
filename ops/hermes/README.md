# Hermes operating context snapshot

This directory is a versioned, sanitized trace of the Hermes context that is
relevant to Marquise operations.

## Included

- `SOUL.md`: Aster's identity and operating mandate.
- `USER.md` and `MEMORY.md`: persistent user and operating memories.
- `profiles/mara/SOUL.md`: Mara's specialist Bot charter.
- `config.sanitized.yaml`: non-secret Hermes configuration with sensitive
  values replaced by placeholders.
- `manifest.json`: hashes and source mapping for the snapshot.

## Explicitly excluded

Secrets and runtime state are never copied: `.env`, OAuth/auth files,
passwords, session transcripts, SQLite databases, logs, caches, locks, and
platform credentials. The source files remain in the Hermes home on the host.

## Sync process

Run from the Marquise repository on the dedicated branch:

```bash
python3 scripts/sync-hermes-state.py
python3 scripts/sync-hermes-state.py --commit --push
```

The script refuses to run on another branch. A scheduled Hermes job runs the
second command periodically and pushes only when the snapshot changed. The
branch can then be reviewed and merged through the normal pull-request flow.

This repository snapshot is an audit trail, not a backup suitable for
restoring a complete Hermes installation.
