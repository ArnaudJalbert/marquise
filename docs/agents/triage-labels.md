# Triage labels

| Canonical role | Tracker label | Meaning |
| --- | --- | --- |
| `bug` | `bug` | Something is broken |
| `enhancement` | `feature` | New feature or improvement |
| `needs-triage` | `needs-triage` | Maintainer must evaluate issue |
| `needs-info` | `needs-info` | Waiting for reporter information |
| `ready-for-agent` | `ready-for-agent` | Fully specified and ready for agent work |
| `ready-for-human` | `ready-for-human` | Requires human implementation |
| `wontfix` | `wontfix` | Will not be actioned |

When a skill names a canonical role, use its corresponding tracker label.

## Category labels

Category labels sit beside the state labels above.

| Label | Use |
| --- | --- |
| `type:feat`, `type:refactor`, `type:idea`, `type:research`, `type:proposal` | Exactly one per issue: what kind of work it is |
| `area:core`, `area:api`, `area:cli`, `area:web`, `area:ci`, `area:infra`, `area:docs` | One or more: which part of the repo it touches |
| `blocked` | Waiting on a dependency; link the blocker |
| `agent:in-progress` | An agent is working on the issue |
| `agent:pr-open` | A PR is open and waiting for review |

`wayfinder:*` labels belong to the wayfinder workflow. Leave them to it.
