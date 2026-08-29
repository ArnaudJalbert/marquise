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
| Strategy, product context, research, briefs, decisions | Marquise Atlas |
| Code, issues, PRs, reviews, CI, releases, deployments | GitHub: [`ArnaudJalbert/marquise`](https://github.com/ArnaudJalbert/marquise) |

Update records at their source. Atlas links to GitHub; it does not copy live status. Arno owns direction, priority, security, material cost, and irreversible commitments. Aster owns this process.

## Workflow

1. Create an Atlas note only when work needs durable context.
2. Link related Atlas and GitHub records. Do not duplicate them.
3. Keep code, discussion, checks, and status in GitHub.
4. Add verified decisions and learnings to Atlas.
5. Update or archive notes when assumptions change.

## Briefs, milestones, and stories

Use a [project brief](../../docs/templates/project-brief.md) only for work spanning several issues or PRs. It explains why the work matters, its boundaries, who decides, and links to GitHub. It is not a task list.

A milestone has an outcome, owner, proof, dependencies, and exit criteria. Track its status in GitHub.

Use the [user-story template](../../docs/templates/user-story.md) for a durable handoff. Acceptance criteria must be testable. Include relevant error, empty, permission, freshness, and rollback cases.

## Pull requests

Keep one focused change per PR. Use the [PR template](../../.github/PULL_REQUEST_TEMPLATE.md). Keep PR discussion, commits, checks, and review state in GitHub. Put only durable decisions and learnings in Atlas.

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
