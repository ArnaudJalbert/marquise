# Changelog

## 0.1.0 (2026-06-06)

### Domain Layer

- **Entities**: `Cinema`, `Movie`, `Screening` with full validation in `__post_init__`
- **Value Objects**: `CinemaId`, `MovieId`, `ScreeningId`, `Showtime`, `ReleaseDate`, `Price`, `DateValue`, `IdValue`
- **Domain Exceptions**: `DomainException`, `MovieError`, `CinemaError`, `ScreeningError`, `MovieNotFoundError`, `CinemaNotFoundError`, `CinemaAlreadyExistsError`, `ScreeningNotFoundError`

### Application Layer

- **Use Case**: `CreateCinemaUseCase` with duplicate name+address detection and UUID collision handling
- **DTOs**: `CreateCinemaRequest`, `CreateCinemaResponse` (frozen dataclasses with validation)
- **Repository Interface**: `CinemaRepository` (abstract, async methods for save/find/exists)
- **Application Exceptions**: `ApplicationError`, `CinemaIdAlreadyExistsError`

### Testing

- Full test coverage for all domain entities and value objects
- Async tests for `CreateCinemaUseCase` with autospecced mocks
- DTO validation tests
- Application exception hierarchy tests
