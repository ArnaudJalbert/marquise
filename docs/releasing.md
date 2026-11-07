# Releasing

Workspace packages release automatically after their version bump merges to `main`.

## Release a package

1. Bump version in affected package's `pyproject.toml`:
   - `packages/marquise-core/`
   - `apps/marquise-api/`
   - `apps/marquise-cli/`
2. Merge pull request.

Release workflow validates every changed package version, builds only that package,
and creates matching tag and private GitHub Release:

- `marquise-core-vX.Y.Z`
- `marquise-api-vX.Y.Z`
- `marquise-cli-vX.Y.Z`

Versions must be numeric `X.Y.Z` bumps. Release assets contain selected package's
wheel and source distribution. Repository access controls keep them private. No
packages are published to PyPI.

Pull-request CI runs the same version and build checks without creating tags,
releases, or uploading assets. GitHub generates release notes from the commits
and pull request associated with each release.

Root `pyproject.toml` is virtual: it has no version of its own.
