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

[`supabase/config.toml`](../supabase/config.toml) is the checked-in Auth
baseline. After linking target project, apply it with:

```bash
supabase config push
```

Confirm matching dashboard settings:

- **Auth > Providers**: disable public sign-ups and enable Anonymous Sign-Ins.
- **Auth > Sessions**: set JWT expiry to 900 seconds (15 minutes).

Invited humans complete email/password signup. Do not enable public signup for
them. Provision a Bot with anonymous sign-in, then use trusted server-side
Supabase administration credentials to set its `app_metadata.marquise_role`.
An anonymous Bot is unprivileged until that metadata is assigned.

`app_metadata.marquise_role` has exactly three values: `member`, `editor`, or
`administrator`. Leave Supabase's reserved JWT `role` claim unchanged.
Metadata and role changes take effect after token refresh or next sign-in.

### Project settings and secrets

Record no credential values in this repository. Keep the Supabase project URL,
publishable key, database connection string, and service-role key in the
project's secret manager. The project URL and publishable key may be supplied
to public clients; the database connection string and service-role key are
server-only. Never expose the service-role key or add it to `.env.example`.

GitHub Actions integration tests require `DATABASE_URL`, `SUPABASE_URL`, and
`SUPABASE_PUBLISHABLE_KEY` secrets. Scheduled imports continue to use their
existing database credentials and do not authenticate through Supabase Auth.

## Integration tests

Integration tests use a real database. Run
[scripts/marquise-test-schema.sql](../scripts/marquise-test-schema.sql) against a
separate test database if needed, then point `DATABASE_URL` at it.

Run integration tests:

```bash
uv run pytest packages/marquise-core/tests/integration_tests/ -q
```

Requires `DATABASE_URL` in `.env`.
