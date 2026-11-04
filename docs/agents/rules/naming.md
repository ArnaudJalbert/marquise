# Naming rules

Read when naming or reviewing variables, parameters, properties, functions, classes, types, or components in Python or TypeScript.

Apply these rules to new names and names changed by the current task. Leave unrelated existing names alone unless the task asks for a rename cleanup.

## Reveal intent

- Choose names that reveal intent. In its surrounding context, a name should make a variable's meaning or a function's or class's responsibility clear without requiring the reader to inspect its implementation.

Marquise examples:

| Don't | Do |
|---|---|
| `x = screening.showtime` | `showtime = screening.showtime` |
| `process(rows)` | `import_screenings(screening_rows)` |
| `class Manager` | `class ScreeningImporter` |

General examples adapted to Python naming style from the 2008 edition's “Meaningful Names” chapter in [*Clean Code*](https://www.oreilly.com/library/view/clean-code-a/9780136083238/chapter02.xhtml):

| Don't | Do |
|---|---|
| `d = ...` | `elapsed_time_in_days = ...` |
| `get_them()` | `get_flagged_cells()` |
| `class Data` | `class CustomerRecord` |

## Match variable names to scope

- Use concise names for variables with narrow scope. Add context and precision as their scope grows. Never use a single-letter value variable or generic type parameter. Use descriptive generic type parameter names such as `ScreeningT`.

```python
def average_price(prices: list[int]) -> float:
    total = sum(prices)
    return total / len(prices)


prices_by_category: dict[str, list[int]] = {}
```

`prices` and `total` are clear inside the function. `prices_by_category` says what the wider-scope mapping stores.

## Use context for functions and classes

- As functions and classes are reused in broader contexts, prefer shorter, more generic names that still identify their domain role. Let the receiver or surrounding API supply detail. Keep public module-level functions specific enough to reveal their operation. Private helpers with narrow use may have longer names that state the exact operation.

```python
screening_repository.delete(screening_id)
self._remove_duplicate_showtimes_from_cinematheque_page(showtimes)
```

`delete` is clear on `screening_repository`. The private helper names the exact work it performs.

## Follow language casing

- In Python, use `snake_case` for variables, parameters, properties, and functions. Use `PascalCase` for classes and types, and `UPPER_SNAKE_CASE` for constants. **Enforced:** `pyproject.toml`.
- In TypeScript, use `camelCase` for variables, parameters, properties, functions, and hooks. Use `PascalCase` for classes, types, and React components. Use `UPPER_SNAKE_CASE` for constants.
- In Python, prefix private helpers with `_`. Use standalone `_` only as a discard target.

## Use nouns for values and classes

- Name variables and properties with nouns or noun phrases. In Python, properties and their setters follow this rule even though they are implemented with methods. Boolean variables and properties also use noun names, such as `posting_eligibility: bool`.
- Name domain classes with nouns or noun phrases. Keep architectural role names, including `Repository`, `Gateway`, `Adapter`, `UseCase`, `InputData`, `OutputData`, `Query`, and `Command`. Use the established action form for command and use-case types, such as `CreateScreeningsCommand`.

| Don't | Do |
|---|---|
| `customer_name_string` | `customer_name: str` |
| `class CalculateInvoice` | `class InvoiceCalculator` |

## Use verbs for functions

- Name action functions with a verb or verb phrase. Python property getters and setters use the property's noun name. Keep established names for `from_` and `to_` conversions, pytest fixtures, and React components.

Python property and setter example:

```python
@property
def title(self) -> str: ...

@title.setter
def title(self, value: str) -> None: ...
```

## Name predicates for questions

- Name functions that answer a yes-or-no question as predicates, such as `is_`, `has_`, or `can_` functions. A command may return `bool` to report success and keep its action name, such as `delete()`.

| Don't | Do |
|---|---|
| `check_payment()` | `is_payment_overdue()` |
| `postable()` | `is_postable()` |

Boolean properties follow the noun rule above.

## Name classes by contract and implementation

- Give base classes, abstract classes, interfaces, and generic types concise names for their broad contract. Make concrete implementations more precise as the inheritance hierarchy deepens, and keep provider names when they distinguish implementations. Apply this only to real inheritance relationships. Do not add inheritance to create a naming hierarchy.

```python
class ScreeningRepository(ABC):
    ...


class SupabaseScreeningRepository(ScreeningRepository):
    ...
```

## Leave language mechanics to the language

- Use annotations, protocols, and inheritance to express types and abstraction. Keep meaningful domain and architectural roles in names, such as `Repository`, `Gateway`, and `UseCase`. Keep provider names when they distinguish concrete implementations. Omit markers that repeat language mechanics, such as `I`, `Abstract`, or `_string`. Keep units that add meaning, such as `timeout_in_seconds`.

| Don't | Do |
|---|---|
| `IOrderRepository` | `OrderRepository` |
| `AbstractPaymentHandler` | `PaymentHandler` |
| `customer_name_string` | `customer_name: str` |
