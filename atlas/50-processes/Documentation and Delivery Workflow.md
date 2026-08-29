---
type: process
status: pilot
owner: Aster
review_date: 2026-09-30
---

# Documentation and Delivery Workflow

Rules for keeping Atlas and GitHub useful.

## Source of truth

| Concern | Source |
|---|---|
| Broad, lasting strategy, principles, processes, decisions, validated learning | Marquise Atlas |
| Planning, brainstorming, research, proposals, task context | GitHub Issues |
| Code, PRs, reviews, CI, releases, deployments | GitHub: [`ArnaudJalbert/marquise`](https://github.com/ArnaudJalbert/marquise) |

GitHub Issues are the planning record. Use `type:idea`, `type:research`, or `type:proposal`, plus an existing area label when relevant. Use `blocked` only when work is waiting on a dependency. Atlas links to GitHub; it does not copy live status.

## Workflow

1. Create a GitHub Issue for planning, research, proposals, and work in progress.
2. Keep code, discussion, checks, and status in GitHub.
3. Add only broad, lasting decisions and validated learning to Atlas.
4. Link related Atlas and GitHub records. Do not duplicate them.

## Issues

Use the issue body for the problem, proposal, research findings, acceptance criteria, and links. Use comments for new evidence and decisions.

Use milestones only for outcomes that group several issues. Acceptance criteria must be testable; include relevant error, empty, permission, freshness, and rollback cases.

## Agent tags

Start every Bot-authored Issue, PR, or comment with `[agent:<name>]`. Use `[[to:<name>]]` only when that Bot must review or respond. One target per tag.

```text
[agent:mara] [[to:orson]] Review request: source markup changed.
```

Aster’s router forwards tagged requests. Untagged comments do not notify Bots.

## Pull requests

Every PR must link one issue with `Closes #N`. Keep one focused change per PR. Use the [PR template](../../.github/PULL_REQUEST_TEMPLATE.md). Keep PR discussion, commits, checks, and review state in GitHub. Put only durable decisions and learnings in Atlas.

## Review and merge gates

Reviewers read the brief or issue, rules, full diff, and current-head CI. Comments state the impact and next step. Authors reply `fixed`, `withdrawn`, `accepted-risk`, `escalated-and-decided`, or `non-blocking follow-up`.

Before approval:

- [ ] Acceptance criteria are clear.
- [ ] Required checks passed on the current head.
- [ ] Relevant security, data, migration, performance, and testability risks were checked.
- [ ] An independent reviewer inspected the latest diff and substantive comments are resolved.

Approval is not authority to merge or deploy. After an authorized merge or deploy, verify the result and record durable learning in Atlas.

## Sources

- GitHub Docs: [PR templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository), [standardizing PRs](https://docs.github.com/en/pull-requests/reference/managing-and-standardizing-pull-requests), [reviews](https://docs.github.com/en/pull-requests/reference/pull-request-reviews), and [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
- Atlassian: [single source of truth](https://www.atlassian.com/work-management/knowledge-sharing/documentation/building-a-single-source-of-truth-ssot-for-your-team).
- Asana: [project milestones](https://www.asana.com/resources/project-milestones).
- Bill Wake: [INVEST](https://xp123.com/articles/invest-in-good-stories/).
- Google Engineering Practices: [small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html).
