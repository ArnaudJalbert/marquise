# Database setup

Bootstrap Supabase (PostgreSQL) for local development and integration tests.

Env vars → [CONTRIBUTING.md](../CONTRIBUTING.md#environment-variables).

---

## Schema

1. Create a Supabase project (or local PostgreSQL).
2. Open the SQL Editor and run [scripts/marquise-schema.sql](../scripts/marquise-schema.sql).
3. Copy `.env.example` → `.env` and set `DATABASE_URL` to your connection string.

Optional: `DATABASE_SCHEMA` (default `marquise`).

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
Generate one key per intended action and reuse it for retries, including after a
lost response or retryable 503 (`Retry-After: 1`). Reusing successful intent with
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
