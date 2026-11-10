# Issue labels

The GitHub Project's `Status` field is the workflow contract. It controls ticket pickup and handoffs in the autonomous implementation loop. Labels do not authorize work or represent workflow state. Use the [Marquise Kanban](https://github.com/users/ArnaudJalbert/projects/3) to set and read status.

## Work labels

| Label | Use |
| --- | --- |
| `bug` | Something is broken |
| `feature`, `documentation`, `question`, `duplicate` | GitHub's general issue categories, retained for existing issues and direct use |
| `type:feat`, `type:refactor`, `type:idea`, `type:research`, `type:proposal` | Describe the kind of non-bug work |
| `area:core`, `area:api`, `area:cli`, `area:web`, `area:ci`, `area:infra`, `area:docs` | Describe the repo areas affected. Use one or more |
| `idea` | Keep an idea visible for future consideration. This is a tracking tag; `type:idea` describes the kind of work |
| `specs` | The issue is a spec that defines work, often for child tickets |
| `tickets` | The issue is an implementation ticket that delivers a piece of work |
| `architecture`, `testing`, `technical-debt` | Optional topic tags |
| `ready-for-agent`, `ready-for-human` | Retained legacy routing labels. Project `Status`, not these labels, authorizes or routes work |

`wayfinder:*` labels belong to the wayfinder workflow. Leave them to it.

Idea, spec, and ticket labels describe what an issue represents. They can sit beside type and area labels, and they do not change Project `Status` or authorize implementation.

Specs are parent issues. Create each work ticket as a direct child of its spec using GitHub's native sub-issue relationship. Milestones are long-term goals, like sprints. Specs and tickets may join one. When a spec has a milestone, give its tickets the same one. A milestone does not establish parentage. Labels classify issues and do not establish parentage.

## Workflow status

Use the Project `Status` values documented in the [autonomous implementation loop](https://github.com/users/ArnaudJalbert/projects/3): `Backlog`, `Scoping`, `Ready`, `In progress`, `In review`, `Reviewed`, `Blocked`, `Done`, and `Canceled`. In particular, `Blocked` is a board status for work needing Arnaud's intervention, not an issue label for an ordinary dependency wait.

Do not use issue labels to infer status or migrate existing issues unless Arnaud requests it. The autonomous loop reads the Project `Status` field.
