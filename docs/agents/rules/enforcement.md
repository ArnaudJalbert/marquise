# Rule enforcement map

Read when adding a rule, adding a check, or deciding what to verify at each stage of a change.

Each rule has one home: a topic file here, or a shared `coding-*` skill. This map only says how and when Marquise checks it.

## Existing code

- Much existing code predates these rules. Fix violations as you touch the code: every new or changed function and use case follows the rules, and code you work in gets fixed along the way.
- Don't start a change just to fix old violations unless it is the task.
- Leave the automated checks as Planned until enough code complies to turn one on without a large cleanup.

## When

| Stage | What runs | Catches |
|---|---|---|
| Writing | The author reads the matching rule file and shared coding skill from [AGENTS.md](../../../AGENTS.md#rules) | Design: what a use case does, how it is split, what names mean |
| Before commit | `uv run ruff format .`, `uv run ruff check .`, `uv run ty check packages/marquise-core/src`, unit tests | Everything automated, in seconds |
| CI | The same commands in `.github/workflows/quality.yml`, plus integration tests | Everything automated, on every push |
| Review | The reviewer follows [review-and-delivery](review-and-delivery.md#review) | Everything marked Review below |

## What

Check `Rules test` is a planned AST test in `packages/marquise-core/tests/unit_tests/`, in the style of `test_use_case_architecture.py`. Move a rule's status to Enforced, and add its `**Enforced:**` tag, when its check lands.

### Use cases

| Rule | Home | Check | Status |
|---|---|---|---|
| Dependencies are required, with no default or `\| None` | `coding-use-cases` | Rules test | Planned |
| A use case never resolves a dependency | `coding-use-cases` | Rules test: no calls in `__init__` | Planned |
| Only a coordinator injects use cases | `coding-use-cases` | Rules test: injects a use case means no loops or conditions | Planned |
| Injected use cases are imported under `TYPE_CHECKING` | `coding-use-cases` | Rules test | Planned |
| Self-contained on the first pass | `coding-use-cases` | Review. A later sharing step is allowed, so a test can't tell them apart | Review |
| No function outside the class | `coding-use-cases` | Rules test | Planned |
| `execute` is the only public member | `coding-use-cases` | Rules test | Planned |
| `execute` has a complete docstring | `coding-use-cases` | Rules test: `Args` and `Returns` present | Planned |
| `execute` reads as named steps, top-down order | `coding-use-cases` | Review | Review |
| A use case does one job | `coding-use-cases` | Review | Review |
| A command returns IDs, and data comes from a query | `coding-use-cases` | Review | Review |
| A coordinator has no loops or conditions | `coding-use-cases` | Rules test | Planned |
| Inner `InputData` and `OutputData`, never reused | `coding-use-cases` | `packages/marquise-core/tests/unit_tests/application/test_use_case_architecture.py`; its allowlist only shrinks | Enforced |
| `InputData` checks its types | `coding-use-cases` | Rules test: `isinstance` in `__post_init__` | Planned |
| Input stops at `execute` | `coding-use-cases` | Rules test: no private method or inner class uses an input type | Planned |
| Entities first, then repository and reader data classes, then an inner class | `coding-use-cases` | Review | Review |
| No big tuples or complicated dicts | `coding-use-cases` | Review | Review |
| No fallbacks | `coding-use-cases` | Review, with Rules test flagging `except Exception` | Partly planned |
| Failure raises, output never carries one | `coding-use-cases` | Review | Review |
| Application limits raise use-case-specific `ApplicationError`s | `coding-use-cases` | Review | Review |
| Safe to run again | `coding-use-cases` | Review and integration tests | Review |
| Always logs | `coding-use-cases` | Rules test: module has a logger and uses it | Planned |
| Log levels, no logging before raising, no personal data | `coding-use-cases` | Review | Review |
| Test only through `execute` | `coding-use-cases` | Rules test: no private call in use case tests | Planned |
| Mock with autospec | `coding-use-cases` | Rules test: no bare `Mock()` for dependencies | Planned |
| Mocks and the use case come from fixtures | `coding-use-cases` | Review | Review |

### Functions

| Rule | Home | Check | Status |
|---|---|---|---|
| 10 body lines at most | `coding-functions` | Rules test, exempting functions with no branching | Planned |
| 2 levels of nesting at most | `coding-functions` | Rules test | Planned |
| 3 arguments at most, constructors exempt | `coding-functions` | Rules test. Ruff's `PLR0913` can't exempt constructors | Planned |
| No boolean argument | `coding-functions` | Rules test | Planned |
| One job, extract until nothing more can be extracted | `coding-functions` | Review | Review |
| Check for `None` once | `coding-functions` | Review | Review |
| No unexpected side effects | `coding-functions` | Review | Review |

### Naming

| Rule | Home | Check | Status |
|---|---|---|---|
| Casing | `coding-naming` | Ruff `N` in `pyproject.toml` | Enforced |
| No single-letter variables | `coding-naming` | Rules test | Planned |
| Yes-or-no functions use `is_`, `has_` or `can_` | `coding-naming` | Rules test: functions returning `bool` | Planned |
| Functions start with a verb | `coding-naming` | Review. A word list would be unreliable | Review |
| Values are nouns, names reveal intent | `coding-naming` | Review | Review |

### Python and testing

| Rule | Home | Check | Status |
|---|---|---|---|
| Error construction, ownership and API mapping | [python](python.md#errors) | Review against domain boundaries and exception-handler tests | Review |
| Test boundary and layer-specific placement | [testing](testing.md#boundary) | Review and relevant unit and integration suites | Review |
