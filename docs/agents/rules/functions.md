# Function rules

Read when writing or reviewing Python functions and methods in `packages/marquise-core` or `apps/*`.

These rules take precedence over ponytail. When they pull apart, follow these rules, even if the diff gets longer.

## Size

- A function does one thing, and as little as possible.
- Extract functions until nothing more can be extracted. Readable code always beats function call overhead, so overhead is never a reason to keep code inline.
- A function body has 10 lines at most, not counting the docstring, comments or blank lines. There is no minimum.
- Code with no branching that only lists data may be longer: mappings, object construction, SQL text and `InputData` type checks.
- A function body has 2 levels of nesting at most. Use early returns, and extract anything deeper.

## Arguments

- A function takes 3 arguments at most, not counting `self` or `cls`. More than that means it does too much, or it needs a request object or entity. Constructors are exempt, because each dependency is injected separately.
- Never pass a boolean as an argument. Use two functions when one step differs, and two classes when the whole behaviour differs.
- Check for `None` once, where it first appears, then pass on a real value so nothing deeper checks again.

## Side effects

- A function has no unexpected side effects.
- A function that returns data changes nothing.
- A function that changes state says so in its name, and returns only the result of that change, as `save()` returns the saved entity.
