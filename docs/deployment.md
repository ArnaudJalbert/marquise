# Fly.io Deployments

Production deployments are automated via GitHub Actions (`.github/workflows/fly-deploy.yml`) using path-filtered triggers and workspace-root build contexts.

The API and the scheduled import use Supabase. A manual dispatch of
`scheduled-import.yml` runs the same Supabase import.

## Architecture

- **Backend API (`apps/marquise-api`)**: Built from the monorepo root context using `apps/marquise-api/fly.toml`.
- **Web Interface (`web/apps/marquise-interface`)**: Built from the `web` workspace context using `web/apps/marquise-interface/fly.toml`.

After each deploy, the workflow smoke-tests the API (`/health`, `/ready`,
`/v1/cinemas?size=1`) and the interface root. It needs the `FLY_API_TOKEN`
repository secret.

## just recipes

Deployments are defined in the root `justfile`, so local operators and CI run the same commands:

```bash
just deploy-api
just deploy-interface
```

## Validation

Validate Fly configurations before committing changes:

```bash
flyctl config validate --config apps/marquise-api/fly.toml
flyctl config validate --config web/apps/marquise-interface/fly.toml
```
