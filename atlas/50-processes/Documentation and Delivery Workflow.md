---
type: process
status: pilot
owner: Aster
review_date: 2026-09-30
---

# Documentation and Delivery Workflow

A lightweight operating process for turning an approved idea into durable context and a verified GitHub change. It complements [[Knowledge Management Protocol]], [[Code Review and Constructive Challenge]], and [[Technical Review by Orson]].

## 1. Source-of-truth boundaries and governance

| Concern | Source of truth | What Atlas stores |
|---|---|---|
| Strategy, product context, operating rules, agent charters, research, project briefs, decisions | Marquise Atlas | Durable context, links, owners, status, review dates |
| Code, issues, pull requests, reviews, CI, releases, deployments, implementation history | GitHub: [`ArnaudJalbert/marquise`](https://github.com/ArnaudJalbert/marquise) | Links and stable context only; never copied live status |
| Private founder thinking | Arno’s personal vault | Not copied without permission |

The owner of a source updates that source. Atlas may link to an issue or PR, but must not mirror labels, check results, review state, or other volatile GitHub fields. A durable decision or learning belongs in Atlas when it will guide future work; the implementation record remains in GitHub. Arno decides product direction, priority, irreversible commitments, security posture, and material cost. Aster maintains this process and escalates consequential decisions.

## 2. Documentation lifecycle

1. **Frame:** create or update the relevant Atlas note before work when the change needs shared context. Give active notes a `type`, `status`, owner, and review date where useful.
2. **Link:** connect the brief, decision, research, agent/process note, and GitHub issue/PR rather than duplicating content.
3. **Execute:** keep implementation details, discussion, checks, and changing status in GitHub. Keep Atlas focused on durable intent, boundaries, and decisions.
4. **Verify:** update Atlas only with the verified outcome, decision, or learning. Do not report completion from a successful command alone.
5. **Review:** on the review date or when assumptions change, mark the note active, superseded, or archived. Preserve history when it explains a consequential choice.

A note is done when its owner, purpose, current status, related links, and next review or retirement condition are clear.

## 3. Milestones and project briefs

Use an Atlas project brief for a meaningful initiative, cross-cutting change, or work expected to span multiple issues/PRs. Start from [`docs/templates/project-brief.md`](../../docs/templates/project-brief.md). The brief records the problem, desired outcome, non-goals, owner, decision authority, assumptions, risks, milestones, and links to GitHub issues. It does **not** become a second project tracker.

A milestone is a user-visible or decision-useful checkpoint, not a date-shaped task list. Each milestone has an outcome, owner, evidence, dependencies, and exit/acceptance criteria. Keep issue assignment, ordering, status, and completion in GitHub; link the relevant milestone or issues from the brief. Close or revise a milestone when evidence changes, and record consequential scope changes as an Atlas decision.

## 4. User stories and acceptance criteria

Write the smallest useful story around a user or operator outcome:

> As a **[user]**, I want **[capability]**, so that **[benefit]**.

Use [`docs/templates/user-story.md`](../../docs/templates/user-story.md) when a story needs a durable handoff. Acceptance criteria must be observable, testable, and unambiguous. Prefer examples or Given/When/Then scenarios; include error, empty, permission, and data-freshness cases when relevant. A story is ready for implementation when its actor, outcome, scope/non-goals, dependencies, and acceptance criteria are understood. It is done only when every criterion is evidenced by tests, inspection, or an explicitly recorded verification.

## 5. Pull-request template and process

The repository template at [`/.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md) keeps the GitHub record complete without copying it into Atlas. The author should:

1. Link the issue (`Closes #N`) or state the acceptance criteria for a small docs/metadata change.
2. Explain the user/operational outcome, scope, non-goals, risk, migration/rollback plan, and relevant Atlas links.
3. List tests/checks and any follow-up explicitly.
4. Keep one focused change per PR; split unrelated work.
5. Request review only when the latest head is ready and the template is complete.

PR body, discussion, commits, checks, and review state are GitHub records. Atlas records only durable decisions, process changes, and learnings.

## 6. PR review process

The author states the weakest assumption and evidence. An independent reviewer reads the issue/brief, applicable rules, full diff, and current-head CI. Review comments use `Blocker`, `Challenge`, `Suggestion`, or `Question` and include evidence, impact, and next action. Reviewers check acceptance criteria, user impact, correctness, security/privacy, data/migration risk, performance, maintainability, scope, and Clean Architecture boundaries.

The author evaluates each substantive finding and replies with a disposition: `fixed`, `withdrawn`, `accepted-risk`, `escalated-and-decided`, or `non-blocking follow-up`. Material pushes require review of the changed range at the new head. The reviewer withdraws a finding disproved by evidence; neither side treats confidence or a green check as proof. AI-authored work requires a different person, Bot, or fresh temporary reviewer. Follow [[Code Review and Constructive Challenge]] and [[Technical Review by Orson]] for role-specific rules.

## 7. Review and verification gates

Before requesting approval:

- [ ] Source-of-truth boundary is respected; no volatile GitHub status was copied to Atlas.
- [ ] Issue/brief/story and acceptance criteria are linked or recorded in the PR.
- [ ] Scope, risks, migrations, rollback, and user-visible documentation impact are explicit.
- [ ] Required local checks and relevant CI are run on the current head.
- [ ] Clean Architecture, security, data integrity, performance, and testability checks are proportionate to the change.
- [ ] An independent reviewer has inspected the latest diff; the author has dispositioned substantive comments.

Ready to merge means every acceptance criterion and required check passes on the current head, no blocker or consequential challenge remains, migration/rollback evidence is sufficient, and an independent reviewer approved that exact SHA. Approval is not merge or deployment authority. After an authorized merge/deploy, verify the external effect and record durable learning; link GitHub evidence rather than copying its changing state.

## Sources

- GitHub Docs, [Creating a pull request template](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository) — repository PR templates.
- GitHub Docs, [Managing and standardizing pull requests](https://docs.github.com/en/pull-requests/reference/managing-and-standardizing-pull-requests) — standardization and review workflow.
- GitHub Docs, [About pull request reviews](https://docs.github.com/en/pull-requests/reference/pull-request-reviews) — review states and collaboration.
- GitHub Docs, [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) — required checks and review protections.
- Atlassian, [Building a single source of truth](https://www.atlassian.com/work-management/knowledge-sharing/documentation/building-a-single-source-of-truth-ssot-for-your-team) — ownership and discoverability for team knowledge.
- Asana, [Project milestones](https://www.asana.com/resources/project-milestones) — outcome-oriented checkpoints.
- Bill Wake, [INVEST in good stories](https://xp123.com/articles/invest-in-good-stories/) — independent, valuable, estimable, small, and testable stories.
- Google Engineering Practices, [Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html) — focused, reviewable changes.
