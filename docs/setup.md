# Database setup

Bootstrap the PostgreSQL schema (Supabase or a disposable database).

Env vars → [CONTRIBUTING.md](../CONTRIBUTING.md#environment-variables).

---

## Schema

1. Create a Supabase project (or local PostgreSQL).
2. Open the SQL Editor and run [scripts/marquise-schema.sql](../scripts/marquise-schema.sql).
3. Copy `.env.example` → `.env` and set `DATABASE_URL` to your connection string.

Optional: `DATABASE_SCHEMA` (default `marquise`).

## Integration tests

Point `DATABASE_URL` at a disposable PostgreSQL database. The pool fixture loads
[scripts/marquise-schema.sql](../scripts/marquise-schema.sql) into `"marquise-test"`
and truncates the test tables before each test.

Run integration tests:

```bash
uv run pytest integration_tests/ -q
```

Requires `DATABASE_URL` in `.env`.
