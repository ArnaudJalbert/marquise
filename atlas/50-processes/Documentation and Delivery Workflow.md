---
type: process
status: pilot
owner: Aster
review_date: 2026-09-30
---

# Documentation and Delivery Workflow

Turn an approved idea into durable context and a verified GitHub change. This complements [[Knowledge Management Protocol]], [[Code Review and Constructive Challenge]], and [[Technical Review by Orson]].

## Source of truth

| Concern | Source of truth | Atlas stores |
|---|---|---|
| Strategy, product context, operating rules, agent charters, research, briefs, decisions | Marquise Atlas | Durable context, links, owners, status, review dates |
| Code, issues, PRs, reviews, CI, releases, deployments | GitHub: [`ArnaudJalbert/marquise`](https://github.com/ArnaudJalbert/marquise) | Links and durable context only |
| Private founder thinking | Arno’s personal vault | Nothing without permission |

Owners update their own source. Atlas links to GitHub but does not copy volatile status. Arno decides direction, priority, irreversible commitments, security posture, and material cost. Aster maintains this process and escalates consequential decisions.

## Lifecycle

1. **Frame:** create or update an Atlas note when work needs shared, durable context.
2. **Link:** connect briefs, decisions, research, agents, and GitHub records instead of duplicating them.
3. **Execute:** keep implementation, discussion, checks, and live status in GitHub.
4. **Verify:** record only verified outcomes, decisions, and learnings in Atlas.
5. **Review:** revise, supersede, or archive notes when their assumptions change.

## Briefs, milestones, and stories

Use a [project brief](../../docs/templates/project-brief.md) for a meaningful initiative, cross-cutting change, or work spanning multiple issues or PRs. Record the problem, outcome, non-goals, owner, authority, risks, milestones, and GitHub links. It is not a second project tracker.

A milestone is an outcome with an owner, evidence, dependencies, and exit criteria. Track assignments, order, and status in GitHub.

Use the [user-story template](../../docs/templates/user-story.md) when a story needs a durable handoff. Acceptance criteria must be observable and verifiable by a test, inspection, or recorded evidence. Include relevant error, empty, permission, freshness, and rollback cases.

## Pull requests

Keep one focused change per PR. Use the [PR template](../../.github/PULL_REQUEST_TEMPLATE.md): concise changes, checks and results, outcome, and `Closes #N`. Keep PR discussion, commits, checks, and review state in GitHub. Record only durable decisions and learnings in Atlas.

## Review and merge gates

Reviewers inspect the relevant brief or issue, applicable rules, full diff, and current-head CI. Comments state evidence, impact, and next action. Authors disposition substantive findings as `fixed`, `withdrawn`, `accepted-risk`, `escalated-and-decided`, or `non-blocking follow-up`.

Before approval:

- [ ] Acceptance criteria and source-of-truth boundaries are clear.
- [ ] Required local checks and relevant CI passed on the current head.
- [ ] Security, data, migration, performance, and testability risks are proportionate to the change.
- [ ] An independent reviewer inspected the latest diff and substantive comments are resolved.

Approval is not merge or deployment authority. After an authorized merge or deploy, verify the external effect and link its GitHub evidence from Atlas when the learning is durable.

## Sources

- GitHub Docs: [PR templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/creating-a-pull-request-template-for-your-repository), [standardizing PRs](https://docs.github.com/en/pull-requests/reference/managing-and-standardizing-pull-requests), [reviews](https://docs.github.com/en/pull-requests/reference/pull-request-reviews), and [protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
- Atlassian: [single source of truth](https://www.atlassian.com/work-management/knowledge-sharing/documentation/building-a-single-source-of-truth-ssot-for-your-team).
- Asana: [project milestones](https://www.asana.com/resources/project-milestones).
- Bill Wake: [INVEST](https://xp123.com/articles/invest-in-good-stories/).
- Google Engineering Practices: [small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html).
