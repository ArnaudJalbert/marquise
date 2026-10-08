# Database setup

Bootstrap Supabase (PostgreSQL) for local development and integration tests.

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

Fresh schemas persist `source_name` on Screenings. Existing rows remain
source-unknown and cannot be rescheduled automatically. After explicit rollout
approval and a quiet import window, run
[the migration](../scripts/migrations/287-screening-source-provenance.sql).
It uses bounded lock and statement timeouts. Same-source imports may move an
existing Screening only within its Montreal local calendar day; target identity
collisions remain conflicts.

## Auth

[`supabase/config.toml`](../supabase/config.toml) is source of truth. Use
[Supabase Auth configuration](../atlas/50-processes/Supabase%20Auth%20configuration.md)
to push it safely. `supabase config push` applies defaults for omitted keys, so
do not remove existing settings from the file.

Invited humans receive Supabase's account-setup email and choose a password.
Bots start with anonymous sign-in and
have no Marquise access until trusted server code sets
`app_metadata.marquise_role` to `member`, `editor`, or `administrator`. Leave
Supabase's reserved JWT `role` unchanged. Role changes apply after token refresh
or next sign-in.

### Project settings and secrets

Set `SUPABASE_URL` for API JWT verification. The API discovers signing keys at
the project's Auth JWKS endpoint and does not need a service-role key. Supabase
project must use asymmetric JWT signing keys; legacy HS256 projects do not
publish verification keys.

CLI account administration requires `SUPABASE_URL`,
`SUPABASE_PUBLISHABLE_KEY`, and `SUPABASE_SERVICE_ROLE_KEY`. It uses
`MARQUISE_EMAIL` and `MARQUISE_PASSWORD` only when both are configured;
otherwise it prompts for Administrator credentials. The service-role key and
Administrator password are never CLI arguments.

Keep project URL, publishable key, database connection string, and service-role
key in secret manager. URL and publishable key can reach public clients;
database and service-role credentials stay server-side. Never commit values or
put service-role key in `.env.example`.

GitHub Actions integration tests need `DATABASE_URL`, `SUPABASE_URL`, and
`SUPABASE_PUBLISHABLE_KEY`. Scheduled imports keep existing database
credentials and do not use Supabase Auth.

## Screening audit and replay storage

Before deploying audited writes, run the updated production schema script through
the approved schema-change process, first against an isolated database and staging.
The two additive tables, `screening_write_audit` and `screening_write_results`, are
required even for empty PATCH. Applying SQL to production is a separate authorized
step, not part of code deployment. Both schema scripts can be run again safely.

These tables have row-level security enabled with no client policies. Public,
`anon`, and `authenticated` table privileges are revoked. The backend needs a
trusted database role permitted to write these tables; maintainers inspect history
through restricted database access. Do not grant public read or write policies.
History/results have no resource cascade references and survive Screening or Movie
deletion. Successful keys have no expiry; plan storage capacity accordingly.

Audit construction belongs in application use cases. Infrastructure implements
locking and commit/rollback. The same connection holds the Screening change,
optional orphaned Movie cleanup, audit record, and successful replay result. Imports
continue through their existing unaudited path. An audit record is history, not an
automatic restore operation.

Clients must send `Idempotency-Key` and `X-Change-Reason` with every POST/PATCH/DELETE.
Prefer a fresh UUID as the key for each intended action. Reuse it for retries,
including after a lost response or retryable 503 (`Retry-After: 1`). Reusing successful intent with
changed values or reason returns 409. Authentication is checked again on replay.
Never place credentials in keys, reasons, ticket URLs, or other metadata. Raw
requests and authorization headers are not copied into history; arbitrary free
text cannot reliably detect every pasted secret.

Verify the isolated database and staging checks in #253 before approved production
deployment. Nothing in this document authorizes a live schema change or deployment.

## Integration tests

Integration tests use a real database. Run
[scripts/marquise-test-schema.sql](../scripts/marquise-test-schema.sql) against a
separate test database if needed, then point `DATABASE_URL` at it.

Run integration tests:

```bash
uv run pytest packages/marquise-core/tests/integration_tests/ -q
```

Requires `DATABASE_URL` in `.env`.
