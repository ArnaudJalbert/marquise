# Targeted duplicate movie merges

This feature implements #356 against #358. It does not register a runnable
command. #355 owns factory composition, command registration, authorization,
resource lifecycle and assembled-system tests. #359 owns shared schemas and the
metadata repository implementation.

## Integration boundary

- Inject `MovieMetadataRepository` and `MatchMovieExecutor` into
  `MergeMoviesUseCase`. Matching results come from the shared matcher. A failed,
  incomplete or unmatched result refuses the merge.
- Delegate `MovieMetadataRepository.merge(request)` to the isolated
  `SupabaseMovieMergeGateway.merge(request)` using an injected connection pool.
  Do not expose the gateway as a command or bypass the validating use case.
- The CLI module `marquise_cli.merge_movies` consumes the public
  `MergeMoviesExecutor`. `dry_run_merge` returns a result; `format_merge` emits
  exact targets, independent source evidence, stored TMDB identity, revisions,
  screening IDs/counts, unresolved references and collision blockers.
- `apply_merge` requires the explicitly supplied JSON from an unblocked preview,
  with identical survivor and duplicate IDs. It never manufactures approval.
  Return/display blocked outcomes as unsuccessful operations when registering
  commands. Translate invalid JSON, invalid approval and application failures at
  that delivery boundary.

The explicitly named survivor must be the existing TMDB owner when present.
All target identities must be confirmed and agree. Known TMDB identity cannot be
replaced with another provider's ID. The merge writes only screening `movie_id`
and deletes duplicate movies. It never enriches or assigns a new identity.

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

No schema or migration is introduced here. Both existing schemas and future
metadata columns are read through whole-row snapshots. #359 must supply the
metadata repository and its shared schema lifecycle; #355 must verify assembled
composition before exposing these handlers.

Reverting this implementation disables the capability. A committed data merge
has no automatic reverse operation. Keep the approved preview and a separately
reviewed backup/restore procedure before any separately authorized live apply.
No live provider, production database, migration, merge or deployment was used
to implement this feature.

## Release coordination

CLI #354, PR https://github.com/ArnaudJalbert/marquise/pull/365, owns v0.1.16.
This change retains that exact dated changelog entry and advances CLI to v0.1.17
in pyproject and the workspace lockfile. The retained v0.1.16 entry is release
coordination history, not a claim that the refresh handler is included in this
branch. Integrate #354 before declaring the combined stack ready. Both PRs keep
the contract branch as their base. Revalidate shared release files in actual merge
order. This branch advances core once, from 0.2.29 to 0.2.30; the parallel core
tracks also need release reconciliation at integration.
