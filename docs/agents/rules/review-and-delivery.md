# Review and delivery rules

Read when opening, reviewing or merging a pull request.

## Pull requests

- One focused change per PR, linked with `Closes #N`. A trivial docs or metadata PR may state its acceptance criteria in the body instead.
- Use [the PR template](../../../.github/PULL_REQUEST_TEMPLATE.md).
- Acceptance criteria are testable and cover relevant error, empty, permission, freshness and rollback cases.
- Bump each affected package version once per PR and add one changelog section: [docs/releasing.md](../../releasing.md).

## Review

- AI-authored code is reviewed by a different person, Bot or fresh reviewer.
- Evidence beats opinion: tests, measurements, code or documented constraints.
- The reviewer leads with the strongest material objection. With none, they state what they tried to falsify and the residual risk.
- Authors weigh feedback on evidence; reviewers withdraw findings the evidence disproves.
- A push with substantive changes gets its changed range re-reviewed.

## Ready to merge

- Required checks are green on the current head.
- An independent reviewer approved that head, and no blocking thread is open.
- Migrations carry compatibility and rollback evidence.

Approval is not authority to merge or deploy. Arno decides product direction, major architecture, irreversible migrations, security posture, material cost and priority, and authorizes any Bot merge or deploy.

After an authorized merge or deploy, verify the real effect (production, data or operations) before calling the work done.
