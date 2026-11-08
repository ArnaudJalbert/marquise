# Fly.io Deployments

Production deployments are automated via GitHub Actions (`.github/workflows/fly-deploy.yml`) using path-filtered triggers and workspace-root build contexts.

The private self-managed catalog database has a separate manual setup. See
[Fly PostgreSQL setup and recovery](fly-postgres.md) for provisioning, the
configuration-only transfer, costs, and backup limitations. The API and the
daily scheduled import still use Supabase. A manual dispatch of
`scheduled-import.yml` imports into Fly `marquise-db` with
`deploy/import/fly.toml`.

## Architecture

- **Backend API (`apps/marquise-api`)**: Built from the monorepo root context using `apps/marquise-api/fly.toml`.
- **Web Interface (`web/apps/marquise-interface`)**: Built from the `web` workspace context using `web/apps/marquise-interface/fly.toml`.

After each deploy, the workflow smoke-tests the API (`/health`, `/ready`,
`/v1/cinemas?size=1`) and the interface root. It needs the `FLY_API_TOKEN`
repository secret.

## Makefile Shortcuts

Deployments are centrally defined in the root `Makefile` so both local operators and CI workflows execute identical commands:

```bash
make deploy-api
make deploy-interface
```

## Validation

Validate Fly configurations before committing changes:

```bash
flyctl config validate --config apps/marquise-api/fly.toml
flyctl config validate --config web/apps/marquise-interface/fly.toml
```
