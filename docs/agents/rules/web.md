# Web rules

Read when working under `web/`.

## Packages

| Package | Role |
|---|---|
| `packages/marquise-client` | Client protocols, API types, HTTP and mock implementations |
| `packages/components` (`marquise-components`) | UI library: components and filter logic; ships `dist/` and a CSS bundle |
| `apps/marquise-interface` | Routes, client configuration, composition of library exports |

## Dependencies

- Apps depend on packages. Packages never import from apps.
- Consumers import through package `exports` (`marquise-components`, `marquise-components/index.css`), never deep `src/` paths of another package.
- Client implementations live in `marquise-client`, free of app routing and env.

## Components and apps

- Library components receive data and callbacks through props or an injected client. They never fetch on their own.
- Prefer props and injected dependencies over module-level singletons.
- Apps stay thin: routing, the real client, props into library components. Compose library exports instead of duplicating library UI.
- Dev-only demo code (`packages/components/demo/`) stays out of the library build: production entry points never import demo modules. After each build, `packages/components/demo/check-isolation.mjs` fails if `dist/` holds a file that is not `.js`, `.css`, `.map` or `.d.ts`, a path containing `fixtures` or `/demo/`, or a known demo-fixture marker string. It does not detect other demo logic bundled into allowed JS, so review import paths. **Enforced:** `packages/components/demo/check-isolation.mjs`, run by the `marquise-components` build.

## TypeScript

- Strict mode. `any` needs a comment explaining why.
- Each package builds, lints, typechecks and tests independently.

## Tooling

- `pnpm install` only from `web/`. pnpm only, no npm or yarn.
- Commands: [CONTRIBUTING.md](../../../CONTRIBUTING.md#web-from-web).
