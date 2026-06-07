# FastAPI API Implementation Plan

## Dependencies
- `fastapi`, `uvicorn[standard]`

## New files

### `src/marquise/application/use_cases/get_cinema_by_id.py`
- `GetCinemaByIdUseCase` — missing use case, fetches a cinema by ID via `CinemaRepository.find_by_id()`
- InputData: `cinema_id: str`
- OutputData: `id, name, address, city, website`
- Raises `CinemaNotFoundError` (application) if not found

### `src/marquise/infrastructure/fastapi/` (new directory)
- `__init__.py`
- `app.py` — `create_app()` factory, exception handlers, includes routers
- `dependencies.py` — FastAPI dependencies for auth (`get_current_user`, `require_admin`)
- `auth_service.py` — `FastAPIAuthService`, wraps sync Supabase SDK in `run_in_executor`
- `routes/auth.py` — POST `/auth/login`, POST `/auth/logout`, GET `/auth/me`
- `routes/cinemas.py` — GET `/cinemas`, GET `/cinemas/{id}`, POST `/cinemas`, PUT `/cinemas/{id}`, DELETE `/cinemas/{id}`

### New tests
- `tests/unit_tests/infrastructure/fastapi/test_auth_routes.py`
- `tests/unit_tests/infrastructure/fastapi/test_cinema_routes.py`

## Auth strategy
- **Bearer JWT** via `Authorization` header
- `POST /auth/login` → email/password → Supabase `sign_in_with_password` → returns JWT
- Protected routes validate token via Supabase `get_user()` (wrapped in executor, SDK is sync)
- Admin check (`is_admin` in `app_metadata`) for write operations

## Route summary

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | No | Login → returns access_token, refresh_token, user |
| POST | `/auth/logout` | Yes | Sign out |
| GET | `/auth/me` | Yes | Current user profile |
| GET | `/cinemas` | No | List all cinemas (public) |
| GET | `/cinemas/{id}` | No | Get cinema by ID (public) |
| POST | `/cinemas` | Admin | Create cinema |
| PUT | `/cinemas/{id}` | Admin | Update cinema |
| DELETE | `/cinemas/{id}` | Admin | Delete cinema |

## Error handling
- Domain exceptions → HTTPException (400/404/409)
- Auth failures → 401 Unauthorized
- Admin check failure → 403 Forbidden

## What stays unchanged
- All existing `domain/`, `application/`, `interface_adapters/` code
- CLI app and commands
- Existing tests
