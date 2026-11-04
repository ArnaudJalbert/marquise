# Naming rules

Read when naming or reviewing variables, parameters, properties, functions, classes, types, or components in Python or TypeScript.

Apply these rules to new names and names changed by the current task. Leave unrelated existing names alone unless the task asks for a rename cleanup.

## Reveal intent

- Choose names that reveal intent. A reader should understand what a value means or what a function or class is responsible for without inspecting its implementation.

| Don't | Do |
|---|---|
| `process(rows)` | `import_screenings(rows)` |
| `class Manager` | `class ImportScreeningsCommand` |

The class example uses Marquise's existing command form. This unrelated example shows the same principle for values:

| Don't | Do |
|---|---|
| `d = ...` | `elapsed_time_in_days = ...` |
| `get_them()` | `get_flagged_cells()` |

These examples are adapted to Python casing from the 2008 edition's "Meaningful Names" chapter in [*Clean Code*](https://www.oreilly.com/library/view/clean-code-a/9780136083238/chapter02.xhtml).

## Prefer clarity over brevity

- Prefer a longer name that reveals intent over a shorter name that makes the reader decode it. A few extra characters cost less than repeatedly deciphering a name during maintenance.

| Don't | Do |
|---|---|
| `for c in customers:` | `for customer in customers:` |
| `acct` | `customer_account` |

## Name variables by scope

- Use concise names for variables with narrow scope. Add context and precision as their scope grows.

```python
def average_price(prices: list[int]) -> float:
    total = sum(prices)
    return total / len(prices)


prices_by_category: dict[str, list[int]] = {}
```

`prices` and `total` are clear inside the function. `prices_by_category` says what the wider-scope mapping stores.

## Match function names to scope

- For functions used across broad contexts, use concise names that still identify their domain role. Let the receiver or surrounding API supply detail.
- For private helpers with narrow use, use precise names that state the exact operation.

```python
screening_repository.delete(screening_id)
self._remove_duplicate_showtimes_from_cinematheque_page(showtimes)
```

## Never use single-letter variables

- Give every variable a name with at least two letters that reveals its meaning.
- In Python, use `_` only for a value intentionally discarded.

## Name values and properties with nouns

- Name variables and properties with nouns or noun phrases, including boolean values such as `postability: bool`.
- Name Python properties and their setters with the property's noun, even though they are implemented with methods.

```python
@property
def title(self) -> str: ...

@title.setter
def title(self, value: str) -> None: ...
```

## Name functions with verbs

- Name action functions with a verb or verb phrase, such as `delete_screening()` or `clear_filters()`.
- Name functions that answer a yes-or-no question with a predicate such as `is_`, `has_`, or `can_`.
- Keep action names when a command returns `bool` to report success, such as `delete_screening()`.

| Don't | Do |
|---|---|
| `check_payment()` | `is_payment_overdue()` |
| `postable()` | `is_postable()` |

## Name classes by role and contract

- Name domain classes with nouns or noun phrases.
- Preserve architectural role names such as `Repository`, `Gateway`, `Adapter`, `UseCase`, `InputData`, `OutputData`, `Query`, and `Command`.
- Use the established action form for command and use-case types, such as `CreateScreeningsCommand`.
- Give base classes, abstract classes, interfaces, and generic types concise names for their broad contract.
- Make concrete class names more precise as the inheritance hierarchy deepens. Keep a provider name when it distinguishes an implementation.
- Apply hierarchy naming only to real inheritance relationships. Do not add inheritance to create a naming hierarchy.

```python
class ScreeningRepository(ABC):
    ...


class SupabaseScreeningRepository(ScreeningRepository):
    ...
```

## Follow language casing

- In Python, use `snake_case` for variables, parameters, properties, and functions. **Enforced:** `pyproject.toml`.
- In Python, use `PascalCase` for classes. **Enforced:** `pyproject.toml`.
- In Python, use `UPPER_SNAKE_CASE` for constants.
- In TypeScript, use `camelCase` for variables, parameters, properties, functions, and hooks.
- In TypeScript, use `PascalCase` for classes, types, and React components.
- In TypeScript, use `UPPER_SNAKE_CASE` for constants.
- Prefix private Python helpers with `_`.

## Follow framework and conversion conventions

- Name pytest fixtures as nouns because they provide values, such as `client` and `factory`.
- Name React components as nouns in `PascalCase`, such as `MovieSchedule`.
- Name React hooks in `camelCase` with the `use` prefix, such as `useMovieSchedule`.
- Name React callback props with the `on` prefix and the event or action, such as `onSelection` or `onLoadWeek`.
- Name conversion functions with the established `from_<source>` or `to_<target>` form, such as `from_screening()` or `to_datetime()`.

## Leave language mechanics to the language

- Use annotations, protocols, and inheritance to express types and abstraction.
- Keep names focused on domain intent instead of repeating type or abstraction markers such as `I`, `Abstract`, or `_string`.
- Keep units that add meaning, such as `timeout_in_seconds`.

| Don't | Do |
|---|---|
| `IOrderRepository` | `OrderRepository` |
| `AbstractPaymentHandler` | `PaymentHandler` |
| `customer_name_string` | `customer_name: str` |
