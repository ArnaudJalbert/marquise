# Technical Debt & TODO

## Domain: Screening Entity References Full Objects

`Screening` currently holds full `Movie` and `Cinema` entity objects (not just their
IDs). This couples entities together in a way that is inconsistent with Clean
Architecture principles, where entities should reference each other by ID only.

### Why it matters

- Loading full entities forces all callers to fetch related data even when they
  only need the ID (e.g., listing just screening IDs for a calendar view).
- Schema migrations or API changes to `Movie` / `Cinema` could force changes to
  `Screening` tests and logic.
- It blurs the boundary between domain entities and application-layer DTOs.

### Desired fix

1. Change `Screening.movie_id` from `Movie` to `MovieId` (value object).
2. Change `Screening.cinema_id` from `Cinema` to `CinemaId` (value object).
3. Move any cross-entity logic (e.g., "is this movie playing at this cinema")
   into the application layer (use cases).
4. Update all tests accordingly.
5. Update `Screening.__str__()` to not rely on full entity reference.