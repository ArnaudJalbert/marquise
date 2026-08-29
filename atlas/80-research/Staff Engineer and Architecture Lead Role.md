---
type: research
status: active
date: 2026-08-29
owner: Aster
review_date: 2026-09-30
---

# Research: Staff Engineer and Architecture Lead Role

## Conclusion

For Marquise, the useful role is a hybrid **Tech Lead + Architecture Lead**, not a broad CTO. The role needs to remain hands-on while providing technical direction, independent PR review, and safe implementation. The scope is appropriate for a solo founder supported by specialist Bots and temporary agents.

## Implications for Orson

- Set and adjust technical direction in service of the product, rather than pursuing technology for its own sake.
- Combine delivery ownership (scoping, implementation, unblocking) with stewardship of a critical and enduring technical area.
- Keep PRs small and independently testable; require a design conversation before a large or cross-cutting change.
- Use automation for repeatable rules and reserve technical review for evidence, trade-offs, architecture, and user-risk judgment.
- Measure whether delivery becomes safer and easier over time—not Orson’s volume of code or review activity.

## Sources

1. Will Larson, [What do Staff engineers actually do?](https://staffeng.com/guides/what-do-staff-engineers-actually-do/) — staff-level technical direction, exploration, organizational context, and hands-on work.
2. Will Larson, [Staff archetypes](https://staffeng.com/guides/staff-archetypes/) — Tech Lead and Architect role distinctions.
3. Google Engineering Practices, [Small CLs](https://google.github.io/eng-practices/review/developer/small-cls.html) — focused changes, related tests, reviewability, and rollback.
4. GitHub Docs, [Managing a branch protection rule](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule) — required reviews, status checks, stale approvals, and conversation resolution.
5. DORA, [Software delivery performance metrics](https://dora.dev/guides/dora-metrics) — delivery throughput/instability and measuring improvement over time.
