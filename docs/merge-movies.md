# Targeted duplicate movie merges

Preview a proposed merge and save its JSON. Apply requires that exact preview,
including the same survivor and duplicates.

```bash
marquise movie merge-preview SURVIVOR DUPLICATE > preview.json
marquise movie merge-apply SURVIVOR DUPLICATE --preview-file preview.json
```

The shared matcher must confirm that every target has the same TMDB identity.
An incomplete lookup or conflict blocks the operation. Refresh metadata with
`marquise movie refresh --movie-id ID` or `marquise movie refresh --all`.

## Approval and transaction guarantees

Preview runs in a read-only repeatable-read transaction. Apply takes table locks
on movies and screenings, and locks other inbound-reference tables before
rechecking their facts. Lock timeout is five seconds; statement timeout is sixty
seconds. These conservative locks can delay imports. They are intentionally
limited to an explicitly requested administrative operation.

Opaque revisions cover the entire movie and screening rows, target roles and
the catalog's stored TMDB ownership map. Changes to unknown/new columns also
invalidate approval. An unrelated TMDB ownership change conservatively requires
a new preview. Apply rechecks source evidence through the matcher and compares
all approved storage facts under the write lock. Foreign-key references outside
the known screening movie link are unresolved and block the merge, including
cascading references and references in other schemas. Composite/non-ID foreign
keys are refused conservatively. Undeclared logical references cannot be found
through PostgreSQL's constraint catalog and must be made explicit before wiring
this operation into a system that has them.

A collision reports both screening IDs and refuses the whole group. Constraint,
lock or timeout failure rolls back the transaction, including any reassignment
already performed. Screening IDs and every source screening field are preserved.
No screening is deleted and no external ID is cleared.

Retry returns `applied` with the same moved screening IDs only if every duplicate
is absent and the survivor is exactly the predicted post-state. Partial removal,
added/missing/changed screenings, changed identity ownership, metadata or
references block it. Retry inference is deliberately conservative, without a new
receipt table or migration. Matching is revalidated on retries too; an unavailable
matcher refuses safely rather than claiming success.

## Migration and rollback

Apply `scripts/migrations/359-movie-enrichment-state.sql` before deploying the
metadata workflows. Reverting the application disables these commands. A
committed data merge has no automatic reverse operation; retain the approved
preview and a separately reviewed backup and restore procedure.
