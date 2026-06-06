# Supabase Cinema Table

This guide walks through setting up the `cinemas` table in your Supabase project
so the `SupabaseCinemaRepository` can persist cinema data.

## Prerequisites

- A [Supabase](https://supabase.com) project (free tier works)
- The `DATABASE_URL` from your project's **Project Settings → Database →
  Connection string** copied into `.env`

## 1. Open the SQL Editor

1. Log in to your [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project
3. Go to **SQL Editor** in the left sidebar
4. Click **New Query**

## 2. Create the schema and table

Paste the following SQL and click **Run**:

```sql
CREATE SCHEMA IF NOT EXISTS marquise;

CREATE TABLE IF NOT EXISTS marquise.cinemas (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    address TEXT,
    city    TEXT,
    website TEXT
);
```

The table is created inside the `marquise` schema, which keeps it separate
from the default `public` schema. Tables in non-`public` schemas are **not
exposed** by Supabase's auto-generated REST API, making them effectively
private from the API layer.

### Schema breakdown

| Column    | Type   | Constraints        | Description                                     |
|-----------|--------|--------------------|-------------------------------------------------|
| `id`      | TEXT   | `PRIMARY KEY`      | UUID string (e.g. `"550e8400-e29b-41d4-a716-446655440000"`) |
| `name`    | TEXT   | `NOT NULL`         | Cinema name                                     |
| `address` | TEXT   | nullable           | Street address                                  |
| `city`    | TEXT   | nullable           | City name (e.g. `"Montreal"`)                   |
| `website` | TEXT   | nullable           | Cinema website URL (e.g. `"https://cinemaparadiso.com"`) |

## 3. Verify the table

Run this query to confirm the table was created:

```sql
SELECT table_schema, column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'cinemas';
```

Expected output:

| table_schema | column_name | data_type | is_nullable |
|--------------|-------------|-----------|-------------|
| marquise     | id          | text      | NO          |
| marquise     | name        | text      | NO          |
| marquise     | address     | text      | YES         |
| marquise     | city        | text      | YES         |
| marquise     | website     | text      | YES         |

## 4. Test schema (for integration tests)

Integration tests use a separate `marquise-test` schema so they never touch
production data.  Run this SQL once to create it:

```sql
CREATE SCHEMA IF NOT EXISTS "marquise-test";

CREATE TABLE IF NOT EXISTS "marquise-test".cinemas (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    address TEXT,
    city    TEXT,
    website TEXT
);
```

!!! note
    The schema name is quoted (`"marquise-test"`) because it contains a hyphen.
    The `marquise` schema used in production does not need quoting in SQL since
    it has no special characters, but the code quotes it automatically for safety.

## 5. Run the integration tests

From the project root:

```bash
uv run pytest tests/integration -v
```

All 8 tests should pass, confirming that:

- `save` inserts and updates rows
- `find_by_id` retrieves by primary key
- `find_by_name_and_address` matches by name + address (including `NULL`)
- `exists_by_id` checks presence correctly

## Connection string

Your `.env` file should contain:

```
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

You can copy this from **Project Settings → Database → Connection string** in the
Supabase dashboard. If your password contains special characters (`#`, `@`, `%`),
they are automatically handled by the `sanitize_dsn()` utility in the codebase.

## Troubleshooting

### `No route to host`

The hostname may resolve to an IPv6 address. Whitelist your machine's IP in
**Supabase Dashboard → Database → IP Restrictions**, or ensure IPv6 routing is
enabled on your network.

### `database "postgres" does not exist`

Some Supabase projects use a differently named database. Check your connection
string — the database name is the last path segment of the URL.