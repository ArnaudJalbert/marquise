# Review and delivery rules

Read when filing an issue, or opening, reviewing or merging a pull request.

## Issues

- Acceptance criteria are testable and cover relevant error, empty, permission, freshness and rollback cases.
- Milestones group several issues under one outcome.

## Branches and commits

- Branch prefixes: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`.
- Commit messages: `type(scope): concise description`, with types `feat`, `fix`, `refactor`, `test`, `docs`, `chore`.

## Pull requests

- One focused change per PR, linked with `Closes #N`. A trivial docs or metadata PR may state its acceptance criteria in the body instead.
- Use [the PR template](../../../.github/PULL_REQUEST_TEMPLATE.md).
- The author states the risks and the weakest assumption.
- Bump each affected package version once per PR: [docs/releasing.md](../../releasing.md).

## Review

- AI-authored code is reviewed by a different person or a fresh agent that did not write it.
- The reviewer reads the issue, the matching rules, the full diff and current-head CI.
- The reviewer confirms every rule marked Review in [enforcement](enforcement.md) that applies to the change, including the shared `coding-use-cases`, `coding-functions` and `coding-naming` skills.
- Evidence beats opinion: tests, measurements, code or documented constraints.
- The reviewer leads with the strongest material objection. With none, they state what they tried to falsify and the residual risk.
- Authors weigh feedback on evidence; reviewers withdraw findings the evidence disproves.
- A push with substantive changes gets its changed range re-reviewed.
- In the autonomous loop, the review run first runs `uv run --no-project --python 3.13 scripts/agents/pr_evidence.py --repo ArnaudJalbert/marquise --pr N`. It proves green CI on the head, a test change or a stated reason for none, a filled template, a `Closes #N` line and a reviewable diff size. Its failed checks are findings, and the reviewer agent does not re-check them. Tests: `uv run pytest -o pythonpath=scripts/agents scripts/agents`.

## Ready to merge

- Required checks are green on the current head.
- An independent reviewer approved that head, and no blocking thread is open.
- Security, data, migration, performance and testability risks were checked. Migrations carry compatibility and rollback evidence.

Approval is not authority to merge or deploy. Arno, or a human Arno delegates, merges and deploys. Arno decides product direction, major architecture, irreversible migrations, security posture, material cost and priority.

After an authorized merge or deploy, verify the real effect (production, data or operations) before calling the work done.
