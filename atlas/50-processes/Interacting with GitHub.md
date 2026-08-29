---
type: process
status: active
owner: Aster
review_date: 2026-09-30
---

# Interacting with GitHub

## Purpose

Provide the shared, verified procedure for Aster and specialist Bots to interact with GitHub. This process covers authentication, repository access, read operations, external changes, and read-back verification. Workflow-specific procedures add their own acceptance criteria and decision gates.

GitHub is the source of truth for Marquise code, issues, pull requests, reviews, CI, releases, deployments, and implementation history.

## Required repository

- Repository: `ArnaudJalbert/marquise`
- Remote: `https://github.com/ArnaudJalbert/marquise.git`
- Outside the repository, pass `--repo ArnaudJalbert/marquise` explicitly.

## Access check

Use the installed GitHub CLI at `/opt/data/bin/gh`. It may not be on the current shell’s `PATH`, so `gh` or `command -v gh` alone is not a sufficient installation check.

Run these checks before GitHub work:

```bash
/opt/data/bin/gh --version
/opt/data/bin/gh auth status
/opt/data/bin/gh repo view ArnaudJalbert/marquise
```

Confirm the authenticated account and the required repository permission before performing a write. Do not expose token values in output, logs, chat, Atlas, or repository files.

If the absolute-path CLI is missing, unauthenticated, or cannot access the exact repository, stop and report the blocker. Do not guess credentials, substitute a local repository state for GitHub access, or claim completion.

## Standard workflow

1. **Read context first.** Read the relevant Atlas notes, repository `AGENTS.md`, `CONTRIBUTING.md`, and the applicable workflow procedure.
2. **Verify access.** Run the absolute-path checks above and confirm the target repository.
3. **Inspect before changing.** Search existing issues, pull requests, branches, labels, milestones, or files to avoid duplicates and understand current state.
4. **Make the smallest authorized change.** Respect the decision boundary for the workflow. Do not merge, deploy, change production data, change secrets, or change product scope without the required approval.
5. **Read back the exact target.** Retrieve the created or modified GitHub record and verify its title, body, labels, assignees, milestone, state, links, and other relevant fields.
6. **Report evidence.** Include the exact URL or identifier, commands run, result, remaining uncertainty, and any blocker. A successful command is not sufficient without read-back.

## Issues and milestones

Use `/opt/data/bin/gh issue` and `/opt/data/bin/gh api` with the explicit repository where appropriate. Before creating an issue or milestone:

- Search for duplicates by title, symptom, subsystem, and related issue/PR.
- Confirm the requested title, body, labels, assignees, and milestone.
- Use the smallest useful issue body with evidence, user impact, expected/actual behavior, scope, and acceptance criteria.
- Read back the created issue or milestone and record its URL/number.

## Pull requests and code

Follow [[Documentation and Delivery Workflow]] for the PR template, acceptance criteria, review, CI, and verification gates. Use the repository’s [[../../CONTRIBUTING|CONTRIBUTING.md]] for exact branching, test, and commit commands.

Never treat a PR as proof that a bug is fixed. Verification requires the relevant review, merge, deployment, and post-merge checks when those actions are authorized.

## Secrets and failure handling

- Keep GitHub credentials in the machine-wide GitHub CLI credential store used by `/opt/data/bin/gh` (normally `/opt/data/.config/gh/hosts.yml`).
- This credential store is shared by Aster and specialist Bots on this host; do not create or require a separate GitHub token in each Hermes profile.
- Never paste tokens into Telegram or commit them.
- Do not print credential files or include tokens in diagnostic output.
- Prefer the existing authenticated `/opt/data/bin/gh` installation rather than asking Arno to reconfigure authentication for each Bot.
- If access fails, check the absolute CLI path and `auth status` before escalating.
- If the issue is missing evidence, duplicate work, unclear scope, or insufficient permission, report that specific blocker instead of creating speculative work.

## Related processes

- [[Documentation and Delivery Workflow]]
- [[Knowledge Management Protocol]]
- [[Code Review and Constructive Challenge]]
