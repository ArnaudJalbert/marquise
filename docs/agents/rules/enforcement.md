# Rule enforcement map

Read when adding a rule, adding a check, or deciding what to verify at each stage of a change.

Each rule has a home in its topic file. This map only says how and when it is checked.

## Existing code

- Much existing code predates these rules. Fix violations as you touch the code: every new or changed function and use case follows the rules, and code you work in gets fixed along the way.
- Don't start a change just to fix old violations unless it is the task.
- Leave the automated checks as Planned until enough code complies to turn one on without a large cleanup.

## When

| Stage | What runs | Catches |
|---|---|---|
| Writing | The author reads the matching rule file from [AGENTS.md](../../../AGENTS.md#rules) | Design: what a use case does, how it is split, what names mean |
| Before commit | `uv run ruff format .`, `uv run ruff check .`, `uv run ty check packages/marquise-core/src`, unit tests | Everything automated, in seconds |
| CI | The same commands in `.github/workflows/quality.yml`, plus integration tests | Everything automated, on every push |
| Review | The reviewer follows [review-and-delivery](review-and-delivery.md#review) | Everything marked Review below |

## What

Check `Rules test` is a planned AST test in `packages/marquise-core/tests/unit_tests/`, in the style of `test_use_case_architecture.py`. Move a rule's status to Enforced, and add its `**Enforced:**` tag, when its check lands.

### Use cases

| Rule | Home | Check | Status |
|---|---|---|---|
| Dependencies are required, with no default or `\| None` | [dependencies](use-cases/dependencies.md) | Rules test | Planned |
| A use case never resolves a dependency | [dependencies](use-cases/dependencies.md) | Rules test: no calls in `__init__` | Planned |
| Only a coordinator injects use cases | [dependencies](use-cases/dependencies.md) | Rules test: injects a use case means no loops or conditions | Planned |
| Injected use cases are imported under `TYPE_CHECKING` | [dependencies](use-cases/dependencies.md) | Rules test | Planned |
| Self-contained on the first pass | [dependencies](use-cases/dependencies.md) | Review. A later sharing step is allowed, so a test can't tell them apart | Review |
| No function outside the class | [structure](use-cases/structure.md) | Rules test | Planned |
| `execute` is the only public member | [structure](use-cases/structure.md) | Rules test | Planned |
| `execute` has a complete docstring | [structure](use-cases/structure.md) | Rules test: `Args` and `Returns` present | Planned |
| `execute` reads as named steps, top-down order | [structure](use-cases/structure.md) | Review | Review |
| A use case does one job | [structure](use-cases/structure.md) | Review | Review |
| A coordinator has no loops or conditions | [structure](use-cases/structure.md) | Rules test | Planned |
| Inner `InputData` and `OutputData`, never reused | [input-and-output](use-cases/input-and-output.md) | `test_use_case_architecture.py` | Enforced |
| `InputData` checks its types | [input-and-output](use-cases/input-and-output.md) | Rules test: `isinstance` in `__post_init__` | Planned |
| Input stops at `execute` | [input-and-output](use-cases/input-and-output.md) | Rules test: no private method or inner class uses an input type | Planned |
| No fallbacks | [failure](use-cases/failure.md) | Review, with Rules test flagging `except Exception` | Partly planned |
| Failure raises, output never carries one | [failure](use-cases/failure.md) | Review | Review |
| Safe to run again | [failure](use-cases/failure.md) | Review and integration tests | Review |
| Always logs | [logging](use-cases/logging.md) | Rules test: module has a logger and uses it | Planned |
| Log levels, no logging before raising, no personal data | [logging](use-cases/logging.md) | Review | Review |
| Test only through `execute` | [testing](use-cases/testing.md) | Rules test: no private call in use case tests | Planned |
| Mock with autospec | [testing](use-cases/testing.md) | Rules test: no bare `Mock()` for dependencies | Planned |

### Functions

| Rule | Home | Check | Status |
|---|---|---|---|
| 10 body lines at most | [functions](functions.md#size) | Rules test, exempting functions with no branching | Planned |
| 2 levels of nesting at most | [functions](functions.md#size) | Rules test | Planned |
| 3 arguments at most, constructors exempt | [functions](functions.md#arguments) | Rules test. Ruff's `PLR0913` can't exempt constructors | Planned |
| No boolean argument | [functions](functions.md#arguments) | Rules test | Planned |
| One job, extract until nothing more can be extracted | [functions](functions.md#size) | Review | Review |
| Check for `None` once | [functions](functions.md#arguments) | Review | Review |
| No unexpected side effects | [functions](functions.md#side-effects) | Review | Review |

### Naming

| Rule | Home | Check | Status |
|---|---|---|---|
| Casing | [naming](naming.md#follow-language-casing) | Ruff `N` | Enforced |
| No single-letter variables | [naming](naming.md#never-use-single-letter-variables) | Rules test | Planned |
| Yes-or-no functions use `is_`, `has_` or `can_` | [naming](naming.md#name-functions-with-verbs) | Rules test: functions returning `bool` | Planned |
| Functions start with a verb | [naming](naming.md#name-functions-with-verbs) | Review. A word list would be unreliable | Review |
| Values are nouns, names reveal intent | [naming](naming.md#reveal-intent) | Review | Review |
