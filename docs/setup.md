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

Invited humans set an email and password. Bots start with anonymous sign-in and
have no Marquise access until trusted server code sets
`app_metadata.marquise_role` to `member`, `editor`, or `administrator`. Leave
Supabase's reserved JWT `role` unchanged. Role changes apply after token refresh
or next sign-in.

### Project settings and secrets

Keep project URL, publishable key, database connection string, and service-role
key in secret manager. URL and publishable key can reach public clients;
database and service-role credentials stay server-side. Never commit values or
put service-role key in `.env.example`.

GitHub Actions integration tests need `DATABASE_URL`, `SUPABASE_URL`, and
`SUPABASE_PUBLISHABLE_KEY`. Scheduled imports keep existing database
credentials and do not use Supabase Auth.

## Integration tests

Integration tests use a real database. Run
[scripts/marquise-test-schema.sql](../scripts/marquise-test-schema.sql) against a
separate test database if needed, then point `DATABASE_URL` at it.

Run integration tests:

```bash
uv run pytest packages/marquise-core/tests/integration_tests/ -q
```

Requires `DATABASE_URL` in `.env`.
