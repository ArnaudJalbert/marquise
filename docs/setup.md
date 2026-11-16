# Database setup

Bootstrap the PostgreSQL schema (Supabase or a disposable database) and apply migrations.

Env vars → [CONTRIBUTING.md](../CONTRIBUTING.md#environment-variables).

---

## Schema

1. Create a Supabase project (or local PostgreSQL).
2. Open the SQL Editor and run [scripts/marquise-schema.sql](../scripts/marquise-schema.sql).
3. Copy `.env.example` → `.env` and set `DATABASE_URL` to your connection string.

Optional: `DATABASE_SCHEMA` (default `marquise`).

### Existing databases: cinema-scoped screening external IDs (#285)

Fresh schemas scope external-ID uniqueness to `(cinema_id, external_id)`.
Different ticketing providers may issue the same ID. Within one Cinema, an ID
still identifies only one Screening, including after a source change. IDs reused
within that Cinema remain conflicts; imports do not overwrite their owners.
Screenings without an external ID are still allowed.

Re-running bootstrap SQL does **not** alter existing tables. After explicit
approval for live rollout:

1. Pause imports and choose a quiet window. The migration takes an exclusive
   lock on `screenings` while rebuilding its unique index, blocking reads and
   writes. Allow for index rebuild time on larger tables.
2. Run [the forward migration](../scripts/migrations/285-cinema-scoped-external-id.sql)
   in the SQL Editor, or with a SQL client configured to stop on the first error.
   It targets `marquise.screenings`. For an existing test or custom schema,
   change that table reference to the correct quoted schema, such as
   `"marquise-test".screenings`, before executing.
3. Both scripts use a 5-second lock timeout and 60-second statement timeout.
   On failure, issue `ROLLBACK` in the same session before retrying. No rows
   are changed; the old constraint remains until the transaction commits.
4. Confirm the named constraint `screenings_external_id_key` covers
   `(cinema_id, external_id)`, then resume imports. Rerun the Cinémathèque
   import only with approval and confirm cross-Cinema IDs no longer skip.

[Rollback SQL](../scripts/migrations/285-cinema-scoped-external-id-rollback.sql)
restores global uniqueness only if every non-null ID remains globally unique.
If cross-Cinema duplicates now exist, PostgreSQL rejects the rollback; issue
`ROLLBACK` and leave cinema-scoped uniqueness in place. Never delete Screenings
or clear their IDs to force rollback. The scripts retain the original constraint
name so existing gateway conflict translation works before and after migration.

### Existing databases: guarded reschedules (#287)

Fresh schemas persist `source_name` on Screenings. Legacy rows remain
source-unknown; current Cinema assignments do not establish historical ownership.
After explicit rollout approval and a quiet import window:

1. Snapshot the affected rows. Apply
   [the additive migration](../scripts/migrations/287-screening-source-provenance.sql)
   before deploying the new library. It leaves existing provenance unknown.
2. With separate approval, apply
   [the five-row Cineplex receipt](../scripts/migrations/287-verified-cineplex-provenance.sql).
   Read-only verification confirmed the exact Screening, Cinema and Movie IDs,
   October 7 old times, and stored Cineplex links with matching `VistaSessionId`
   and `LocationId=9172`. The script rechecks these fields, permits old or corrected
   times, and aborts atomically if any fingerprint differs. It sets only provenance;
   unrelated unknown rows remain unknown. Never broaden it from assignments.
3. Run the normal Cinema import. Verify `rescheduled_count=5`, stable IDs,
   disappearance of the five old times, and no moves on a repeated import.
   Metadata updates count separately; target collisions preserve both rows.

Both scripts use 5-second lock and 60-second statement timeouts. The receipt blocks
catalog writes while checking evidence, so use a quiet window. If either script
fails, `ROLLBACK`, inspect the mismatch, and obtain fresh evidence rather than
weakening guards. The application compares Montreal local calendar days using
local midnights, including 23/25-hour DST days. Different Movies, sources, days,
ambiguous ownership and target collisions are refusals, not merges.

Application rollback may leave the additive column and verified provenance in
place. It does not restore rescheduled times; any time restoration needs its own
reviewed, ID-guarded operation. Do not delete Screenings or clear external IDs to
force a repair. PR checks run gateway/import regressions against disposable
PostgreSQL, without production secrets. No rollout script runs automatically.

### Existing databases: TMDB movie ids (#321)

Apply [the movie-id migration](../scripts/migrations/321-add-movies-tmdb-id.sql)
**before** deploying code that reads or writes `movies.tmdb_id`. Run it through
an approved schema-change process, not from the scheduled import. It adds a
nullable column and a unique index; existing movies keep a NULL id. No movies
are matched or merged by the migration.

The migration targets `marquise.movies`, uses a 5-second lock timeout, and can
be rerun. Run it in a quiet import window, since adding the column and building
the index can block writes. Check that `tmdb_id` exists and that
`movies_tmdb_id_key` is unique before resuming imports. If the migration fails,
roll back its transaction and retry after investigating the lock or data issue.
The additive column can remain if the application is rolled back.

### Existing databases: movie metadata enrichment state (#359)

Apply [the additive lifecycle migration](../scripts/migrations/359-movie-enrichment-state.sql)
before deploying metadata persistence. The prerequisite #321 migration must already
provide `movies.tmdb_id` and its unique index. The new nullable
`metadata_enriched_at TIMESTAMPTZ` records only a successful atomic metadata write.
The internal `movie_reference_revisions` table and screening trigger invalidate
snapshots on reference changes, including insert/delete cycles. Each transaction
that changes a movie's screenings appends one marker. Markers remain after deletion
to prevent old revisions becoming valid again. The table has row-level security
and no client policies and requires a trusted backend role. Snapshot reads count
that movie's markers through the primary-key index; storage grows with committed
reference-writing transactions. Do not prune markers while snapshots may be in
use. Movie writes also change snapshots.
An existing TMDB ID with a NULL stamp remains pending first enrichment. No rows
are matched, enriched, merged, deleted or backfilled by this migration.

The script targets `marquise.movies`. For a disposable test or custom schema,
replace every `marquise.` schema qualifier before running it. Use an approved quiet window.
The transaction has a 5-second lock timeout and 60-second statement timeout;
adding the column and trigger takes locks on movies and screenings. On failure,
issue `ROLLBACK` in the same session and inspect the cause before retrying. Rerunning preserves both
pending rows and existing completion stamps. Bootstrap scripts create the column
for fresh databases but do not upgrade existing tables.

Verify the timestamp column, marker table, screening trigger and unchanged
legacy metadata before enabling metadata persistence. Application rollback can
leave the additive column, table and trigger in place. Dropping the timestamp
would discard successful-enrichment history and is unnecessary. The migration
itself performs no live rollout. Composition-root wiring and end-to-end
verification landed in #355; guarded merge transactions in #356.

### Existing databases: TMDB movie scores (#373)

Apply [the additive score migration](../scripts/migrations/373-add-movies-tmdb-score.sql)
before deploying code that reads or writes `movies.tmdb_rating` or
`movies.tmdb_vote_count`. It adds nullable `DOUBLE PRECISION` and `INTEGER`
columns. Existing rows and metadata remain unchanged, with both scores NULL
until enrichment fetches them. The script targets `marquise.movies`; replace
the schema qualifier for a disposable test or custom schema.

Run it during a quiet window. The transaction has a 5-second lock timeout and
60-second statement timeout. On failure, issue `ROLLBACK` in the same session
before retrying. `ADD COLUMN IF NOT EXISTS` makes reruns safe. Verify both
column types and existing row counts before enabling score reads and writes.

For application rollback, deploy the earlier code and leave the nullable
columns in place. To remove the columns later, first stop score readers and
writers and back up their data; `ALTER TABLE marquise.movies DROP COLUMN
tmdb_rating, DROP COLUMN tmdb_vote_count` permanently deletes stored scores.
The bootstrap scripts create both columns for fresh databases but do not alter
existing tables.

## Integration tests

Point `DATABASE_URL` at a disposable PostgreSQL database. The pool fixture loads
[scripts/marquise-schema.sql](../scripts/marquise-schema.sql) into `"marquise-test"`
and truncates the test tables before each test.

Run integration tests:

```bash
uv run pytest integration_tests/ -q
```

Requires `DATABASE_URL` in `.env`.
