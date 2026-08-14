# Releasing

Version bumps and PyPI releases for workspace packages.

---

## Steps

1. Bump version in the affected package's `pyproject.toml`:
   - `packages/marquise-core/`
   - `apps/marquise-api/`
   - `apps/marquise-cli/`
2. Add a [CHANGELOG.md](../CHANGELOG.md) entry under the current date.
3. Commit: `chore(<pkg>): bump to vX.Y.Z`
4. Tag: `marquise-core-vX.Y.Z` (or `marquise-api-vX.Y.Z`, `marquise-cli-vX.Y.Z`)
5. Push: `git push origin main --tags`

CI builds, publishes to PyPI, and creates a GitHub Release.

Root `pyproject.toml` is virtual — it has no version of its own.
