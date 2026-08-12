# Web Detail Client Corrections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the web workspace typecheck cleanly, query inclusive API date ranges without cross-day leakage, and ignore TypeScript incremental build metadata.

**Architecture:** The FastAPI API accepts inclusive timezone-aware `from` and `to` datetimes. The TypeScript HTTP grid and detail clients will convert a selected UTC `YYYY-MM-DD` date into explicit start-of-day and end-of-day timestamps, rather than approximating an exclusive bound with the next midnight. Tests will verify the emitted query parameters, and workspace configuration will ignore Vite/TypeScript build-info output.

**Tech Stack:** TypeScript 6, Vitest 4, Vite 8, pnpm workspaces, FastAPI REST API.

## Global Constraints

- Keep all web commands inside `web/` and use pnpm 11.x.
- Preserve the public `MovieGridClient` and `MovieDetailClient` interfaces.
- The API `from` and `to` query values are inclusive timezone-aware datetimes.
- Add or update focused Vitest coverage for each behavior change.
- Run `pnpm test`, `pnpm typecheck`, and `pnpm lint` from `web/` before handoff.

---

### Task 1: Correct inclusive UTC date range construction

**Files:**
- Modify: `web/packages/marquise-client/src/http-client.ts`
- Modify: `web/packages/marquise-client/src/http-client.test.ts`
- Modify: `web/packages/marquise-client/src/http-movie-detail-client.ts`
- Modify: `web/packages/marquise-client/src/http-movie-detail-client.test.ts`

**Interfaces:**
- Consumes: `GET /v1/screenings` with inclusive `from` and `to` datetime filters.
- Produces: `HttpMovieGridClient.fetchForDate(date)` and `HttpMovieDetailClient.fetchShowtimes(movie, date)` queries bounded to exactly one UTC calendar day.

- [ ] **Step 1: Write failing assertions for an explicit full-day range**

Update the existing grid and detail-client tests to expect:

```ts
expect(url.searchParams.get("from")).toBe("2026-08-05T00:00:00.000Z");
expect(url.searchParams.get("to")).toBe("2026-08-05T23:59:59.999Z");
```

For `HttpMovieDetailClient.listDates()` with `horizonDays: 3`, expect the upper bound to be `"2026-08-07T23:59:59.999Z"`.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `pnpm --filter marquise-client test -- http-client.test.ts http-movie-detail-client.test.ts`

Expected: FAIL because both clients currently send a date-only `from` and a next-day-midnight `to` bound.

- [ ] **Step 3: Implement explicit UTC day-bound helpers and use them**

In each client module, replace next-day date-only bounds with helpers equivalent to:

```ts
function startOfUtcDay(date: string): string {
  return `${date}T00:00:00.000Z`;
}

function endOfUtcDay(date: string): string {
  return `${date}T23:59:59.999Z`;
}
```

Use `startOfUtcDay(date)` and `endOfUtcDay(date)` in each one-day request. For detail-date discovery, calculate the final displayed date with `addUtcDays(today, this.horizonDays - 1)`, return `[]` without a request when the horizon is zero, and use that date's `endOfUtcDay` value as the inclusive upper bound. Update the JSDoc so it describes inclusive full-day bounds rather than half-open ranges.

- [ ] **Step 4: Run the focused tests to verify they pass**

Run: `pnpm --filter marquise-client test -- http-client.test.ts http-movie-detail-client.test.ts`

Expected: PASS, including the date-query assertions and pagination coverage.

- [ ] **Step 5: Commit the focused client correction**

```bash
git add web/packages/marquise-client/src/http-client.ts web/packages/marquise-client/src/http-client.test.ts web/packages/marquise-client/src/http-movie-detail-client.ts web/packages/marquise-client/src/http-movie-detail-client.test.ts
git commit -m "fix(web): bound showtime queries to UTC days"
```

### Task 2: Restore TypeScript typecheck and ignore generated metadata

**Files:**
- Modify: `web/packages/marquise-client/src/mock-client.test.ts`
- Modify: `web/.gitignore`
- Delete from working tree: `web/apps/marquise-interface/tsconfig.tsbuildinfo`

**Interfaces:**
- Consumes: `MockMovieGridClient.listDates(): Promise<readonly string[]>`.
- Produces: a narrowed `string` date passed to `fetchForDate()` and `fetchShowtimes()`, and no tracked `*.tsbuildinfo` artifacts.

- [ ] **Step 1: Write the type-safe date narrowing**

Replace the unchecked indexed date in the deterministic mock-detail test with an explicit guard:

```ts
const date = (await grid.listDates())[0];
if (date === undefined) {
  throw new Error("mock grid must provide a date");
}
const item = (await grid.fetchForDate(date))[0];
```

This makes `date` a `string` before either client call.

- [ ] **Step 2: Add the generated build-info ignore rule**

Append this focused rule to `web/.gitignore`:

```gitignore
*.tsbuildinfo
```

Remove the existing untracked `web/apps/marquise-interface/tsconfig.tsbuildinfo` artifact; it can always be regenerated by TypeScript.

- [ ] **Step 3: Run workspace checks**

Run: `pnpm test && pnpm typecheck && pnpm lint`

Expected: all workspace tasks pass; `pnpm typecheck` has no `string | undefined` errors.

- [ ] **Step 4: Verify the patch and workspace state**

Run: `git diff --check && git status --short`

Expected: no whitespace errors and no `tsconfig.tsbuildinfo` entry.

- [ ] **Step 5: Commit the typecheck and hygiene correction**

```bash
git add web/packages/marquise-client/src/mock-client.test.ts web/.gitignore
git commit -m "fix(web): restore workspace typecheck"
```

## Self-Review

- Spec coverage: Task 1 fixes inclusive API range behavior and tests it; Task 2 fixes the TypeScript failure and generated artifact reported in branch exploration.
- Placeholder scan: no TODOs or deferred implementation steps remain.
- Type consistency: both client methods continue to receive `string` calendar dates; the test guard narrows the only optional array index before use.
