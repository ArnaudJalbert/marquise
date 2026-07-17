# @marquise/api-client

A typed TypeScript client for the Marquise API. This is an **internal, unpublished** workspace package — consumed by [`marquise-admin`](../../apps/marquise-admin) via the `workspace:*` protocol, never installed from a registry.

## What lives here

A small, dependency-free `fetch` wrapper around the public, read-only `/v1` endpoints exposed by `apps/marquise-api` (movies, cinemas, screenings). Types are hand-written to mirror the backend's Pydantic response models — there is no OpenAPI codegen step.

## Consuming it

```jsonc
// apps/<app>/package.json
"dependencies": {
  "@marquise/api-client": "workspace:*"
}
```

```ts
import { MarquiseApiClient } from '@marquise/api-client'

const client = new MarquiseApiClient({ baseUrl: 'https://marquise-api.fly.dev' })

const movies = await client.movies.list({ title: 'Dune', page: 1, size: 20 })
const cinema = await client.cinemas.get('some-cinema-id')
const screenings = await client.screenings.search({ cinema_id: cinema.id, from: new Date() })
```

## Error handling

Every failed request rejects with a `MarquiseApiError` (never a raw `fetch`/JSON error):

```ts
import { MarquiseApiError } from '@marquise/api-client'

try {
  await client.movies.get('missing-id')
} catch (error) {
  if (error instanceof MarquiseApiError) {
    // error.status, error.errorCode, error.requestId, error.detail
  }
}
```

## Adding an endpoint

1. Add the method to the relevant class under `src/resources/` (or add a new resource file if it's a new top-level resource), using the shared `request()` helper (`src/http.ts`) and `buildQuery()` helper (`src/query.ts`).
2. Add/extend response types in `src/types.ts` to match the backend Pydantic model.
3. Re-export any new param types from `src/index.ts`.
4. Add a test alongside the resource (see `src/resources/movies.test.ts` for the pattern).

## Build

```bash
# From web/
pnpm --filter @marquise/api-client build   # tsc -> dist/ (JS + .d.ts)
pnpm --filter @marquise/api-client lint    # type-check without emitting
pnpm --filter @marquise/api-client test    # vitest
```

`turbo run build` at the workspace root builds this package before any app that depends on it (via `dependsOn: ["^build"]` in [`web/turbo.json`](../../turbo.json)).

## Package details

| | |
|---|---|
| Entry | `src/index.ts` → built to `dist/index.js` + `dist/index.d.ts` |
| Module type | ESM (`"type": "module"`) |
| Build tool | `tsc` (config in [`tsconfig.json`](tsconfig.json)) |
| Runtime requirement | native `fetch` (browsers, Node ≥ 20) |
| Deps | none |
| Test framework | `vitest`, scoped to this package only |
