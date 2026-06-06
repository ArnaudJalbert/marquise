# Marquise Development Guide for AI Agents

**Version**: 1.0  
**Audience**: All developers, with emphasis on AI coding assistants (agents)  
**Purpose**: Authoritative, detailed guide for consistent, high-quality development on Marquise

## 1. Introduction & How to Use This Document

AGENTS.md is the definitive development manual for the Marquise project. Every developer and AI agent working on this codebase **must read and follow** these guidelines.

This document is **prescriptive and detailed**. When instructions say "always" or "never," they are mandatory. Deviations require explicit justification in code comments and documentation.

For AI agents: Use this document as your primary instruction set. Before making any code change, reference the relevant sections below to ensure compliance.

## 2. Project Overview

**Marquise** is an open-source platform for aggregating and exploring movie showtimes in Montreal. It gathers screening data from multiple theaters, normalizes it, and exposes it through a REST API.

**Core Product Principles**:
- Focus on Montreal cinema initially, but architecture supports expansion
- Reliability: structured, validated cinema data
- User-friendly API and evolving application interface
- Clean, maintainable codebase with high test coverage

## 3. Technology Stack

- **Language**: Python 3.13 (strict requirement)
- **Package Manager**: `uv` (all dependency management and command execution)
- **API Framework**: FastAPI (async-first, automatic OpenAPI docs)
- **Database**: MongoDB (PyMongo or MongoEngine) - **must be abstracted behind repository interfaces**
- **Testing**: pytest (with pytest-asyncio for async)
- **Code Quality**: 
  - Ruff (formatting: `uv run ruff format`)
  - Ruff (linting: `uv run ruff check --fix`)
  - Type hints: **mandatory everywhere**
- **Documentation**: MkDocs (to be documented separately)

**No exceptions**: All dependencies are managed via `uv`. Never use `pip` directly.

## 4. Clean Architecture - The Foundation

Marquise strictly follows **Clean Architecture** (also known as Onion or Hexagonal Architecture). This architecture enforces separation of concerns and makes the codebase testable, maintainable, and adaptable.

### 4.1 The Four Layers

```
┌─────────────────────────────────────────┐
│   src/marquise/infrastructure/         │
│   (FastAPI, Config, Database)          │
├─────────────────────────────────────────┤
│   src/marquise/interface_adapters/     │
│   (Repository Implementations)         │
├─────────────────────────────────────────┤
│   src/marquise/application/            │
│   (Use Cases, DTOs, Repository Interfaces)│
├─────────────────────────────────────────┤
│   src/marquise/domain/                 │
│   (Entities, Value Objects, Rules)     │
└─────────────────────────────────────────┘
```

**Dependency Rule**: **Dependencies point inward only**. Outer layers can depend on inner layers, but inner layers **never** depend on outer layers.

### 4.2 Layer Responsibilities

#### **Domain Layer** (innermost, pure business logic)
- **Entities**: 
  - Objects with identity and lifecycle (e.g., `Movie`, `Theater`, `Screening`)
  - Mutable objects that can be modified
  - Business logic methods can modify internal state
- **Value Objects**: Immutable objects defined by their attributes (e.g., `Showtime`, `Price`, `PostalCode`)
- **Domain Services**: Business logic that doesn't naturally belong to an entity
- **Domain Events**: Events that occur within the business logic (optional)

**Entity Rules**:
- Use `@dataclass(kw_only=True, slots=True)` 
- Validate data in `__post_init__` method
- Maintain type hints
- Prefer type safety and validation over mutable state

**Zero dependencies**: Domain layer must NOT import anything from application, interface_adapters, or infrastructure. It can use Python standard library only.

#### **Application Layer** (use cases, orchestrates domain)
- **Use Cases** (or **Interactors**): Application-specific business rules. Each use case represents one user action (e.g., `GetShowtimesQuery`, `AddTheaterCommand`).
- **DTOs** (Data Transfer Objects): Simple data containers for input/output of use cases
  - Must use frozen dataclasses (`@dataclass(frozen=True, slots=True)`)
  - Validation in `__post_init__` method
  - Do NOT use Pydantic models in the application layer
- **Repository Interfaces**: Abstract base classes defining data access contracts (e.g., `ScreeningRepository`, `MovieRepository`)
- **Application Service Interfaces**: Very thin coordination layer (optional, often use cases suffice)

**Dependencies**: Can import from `src/marquise/domain` only. Never depend on infrastructure or interface_adapters.

#### **Interface Adapters Layer** (adapts external data to internal forms)
- **Repository Implementations**: Concrete implementations of repository interfaces using external systems (MongoDB, APIs, file systems)

**Dependencies**: Can import from `src/marquise/application` and `src/marquise/domain`. Never depend on `src/marquise/infrastructure`.

#### **Infrastructure Layer** (external concerns)
- **FastAPI**: Routes, dependencies, application setup
- **Configuration**: Environment variables, settings management
- **Database Connections**: Connection management
- **External Service Integrations**: Third-party APIs (theater APIs, geocoding, etc.)

**Dependencies**: Can import from all inner layers (domain, application, interface_adapters). Should be the only layer with direct database/external dependencies. It imports from interface_adapters to instantiate repository implementations and wire everything together.

### 4.3 Layer Boundaries - Concrete Rules

1. **No circular imports**: If you see them, architecture is broken
2. **Domain never knows about databases, HTTP, or external systems**
3. **Application never knows about databases or HTTP** (only use cases and DTOs)
4. **Infrastructure and interface_adapters implement interfaces defined in application**. They may depend on domain for entities.
5. **Infrastructure depends on application** (use cases, DTOs) and on **interface_adapters** (repository implementations) to wire everything together. It's acceptable to import concrete classes from interface_adapters in infrastructure for type annotations and instantiation.

### 4.4 Example Data Flow

```
HTTP Request → Route (infrastructure) → Use Case (application) 
→ Repository Interface (application) → Repository Implementation (interface_adapters) 
→ Database → Response flows back outward
```

## 5. Development Environment Setup

### 5.1 Prerequisites

- **Python 3.13+** (verify: `python3 --version` or `python --version`)
- **uv** (install if missing: `curl -LsSf https://astral.sh/uv/install.sh | sh`)

### 5.2 First-Time Setup

Open terminal in project root (`/Users/arnaudjalbert/workspace/marquise`):

```bash
# 1. Create virtual environment and install dependencies
uv sync

# 2. Install marquise package in editable mode
uv pip install -e .

# 3. Verify installation
uv run python --version
# Should output: Python 3.13.x

# 4. Run code quality checks (should pass on empty project)
uv run ruff format .
uv run ruff check --fix

# 5. Run tests (there may be none yet)
uv run pytest tests
```

### 5.3 Daily Development Workflow

**Every development session, in this exact order:**

1. Start with `git pull` to ensure you're up-to-date
2. Make your code changes
3. **Immediately format and lint**:
   ```bash
   uv run ruff format .
   uv run ruff check --fix
   ```
4. **Run tests**:
   ```bash
   uv run pytest tests
   ```
5. **Check coverage** (see Testing section for details)
6. Commit with a clear message

**Never commit code that fails linting or tests.**

### 5.4 Adding New Dependencies

Only use `uv`:

```bash
# Add a runtime dependency
uv add fastapi
uv add pymongo

# Add a dev dependency (pytest, ruff already included)
uv add --dev pytest-asyncio
```

Then update `uv.lock`:

```bash
uv lock
```

Commit both `pyproject.toml` and `uv.lock`.

## 6. Code Quality Standards

### 6.1 Type Hints - 100% Mandatory

**Every function, method, lambda, and class method must have complete type hints.**

**Rules**:
- Function arguments: all must have type annotations
- Function returns: always annotate return type (use `None` for void)
- Class attributes: annotate all instance variables in `__init__`
- Local variables: annotate when type is not obvious (encouraged always)
- Use `typing` module: `List`, `Dict`, `Optional`, `Union`, `TypedDict`, `Protocol`, etc.
- Prefer specific types over `Any`. If you need `Any`, add comment explaining why.

**Good example**:
```python
from typing import List, Optional
from datetime import datetime

class ScreeningService:
    def __init__(self, repository: ScreeningRepository) -> None:
        self.repository = repository
    
    async def get_upcoming_showtimes(
        self, 
        theater_id: str, 
        days_ahead: int = 7
    ) -> List[Showtime]:
        """Return upcoming showtimes for a theater."""
        cutoff = datetime.utcnow() + timedelta(days=days_ahead)
        return await self.repository.find_by_theater_and_date_range(
            theater_id=theater_id,
            start_date=datetime.utcnow(),
            end_date=cutoff
        )
```

**Bad example** (missing type hints):
```python
def get_showtimes(theater_id, days_ahead=7):
    # missing type hints - FORBIDDEN
    pass
```

### 6.2 Ruff Formatting and Linting

**Commands** (run these before every commit):
```bash
uv run ruff format .
uv run ruff check --fix
```

**What these do**:
- `ruff format`: Auto-formats code (like Black) - line length 88, consistent styling
- `ruff check --fix`: Auto-fixes lint errors (unused imports, syntax issues, etc.)

**Never manually style code** - let ruff handle it. If code looks weird after formatting, adjust your original style to be ruff-compliant.

**Common violations to avoid**:
- Unused imports (delete them)
- Line too long (ruff will fix automatically)
- Missing docstrings on public modules, classes, functions (add them)
- Ambiguous variable names (use descriptive names)

### 6.3 Test Coverage Requirements

**100% coverage required for**:
- `src/marquise/domain/` layer (all entities, value objects, domain services)
- `src/marquise/application/` layer (all use cases, DTOs, repository interfaces)
- `src/marquise/interface_adapters/` layer (all routes, request/response models)

**Infrastructure layer** (database implementations, external API clients): coverage should be "good" but 100% not strictly required. However, integration tests must cover critical paths.

**Enforcement**:
```bash
uv run pytest tests/ --cov=marquise.domain --cov=marquise.application --cov=marquise.interface_adapters --cov-report=html
```

Open `htmlcov/index.html` to see uncovered lines. **No PR merges with uncovered lines in core layers.**

## 7. REST API Development with FastAPI

### 7.1 Design Principles

- **RESTful**: Use appropriate HTTP methods (GET, POST, PUT, DELETE)
- **Resource-oriented**: URLs represent resources (nouns, not verbs)
- **Status codes**: Use correct HTTP status codes (200, 201, 400, 404, 409, 500, etc.)
- **Async-first**: All I/O operations (database, external API) should be async
- **JSON**: All request/response bodies use JSON

### 7.2 File Structure

```
src/marquise/
├── application/
│   └── dtos/
│       ├── requests.py
│       └── responses.py
├── interface_adapters/
│   └── repositories/ (implementations)
└── infrastructure/
    └── fastapi/
        ├── routes/
        │   ├── movies.py
        │   ├── theaters.py
        │   └── showtimes.py
        ├── dependencies.py
        └── app.py
```

### 7.3 Creating an Endpoint - Step-by-Step

**Step 1**: Define request/response Pydantic models in `src/marquise/application/dtos/`

```python
# src/marquise/application/dtos/requests.py
from pydantic import BaseModel, Field, validator
from datetime import date
from typing import List

class GetShowtimesRequest(BaseModel):
    """Query parameters for getting showtimes."""
    theater_id: str = Field(..., min_length=1, description="Theater ID")
    date: date = Field(..., description="Date to get showtimes for")
    
    @validator('theater_id')
    def validate_theater_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Theater ID cannot be empty")
        return v

class CreateScreeningRequest(BaseModel):
    movie_id: str
    theater_id: str
    start_time: datetime
    availability: Optional[Dict[str, bool]] = None
```

```python
# src/marquise/application/dtos/responses.py
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class ShowtimeResponse(BaseModel):
    id: str
    movie_title: str
    theater_name: str
    start_time: datetime
    available_seats: int
    price: float
    
class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
```

**Step 2**: Create route in `src/marquise/infrastructure/fastapi/routes/`

```python
# src/marquise/infrastructure/fastapi/routes/showtimes.py
from fastapi import APIRouter, Depends, HTTPException, status
from marquise.application.use_cases import GetShowtimesUseCase, CreateScreeningCommand
from marquise.application.dtos.requests import GetShowtimesRequest, CreateScreeningRequest
from marquise.application.dtos.responses import ShowtimeResponse, ErrorResponse
from marquise.infrastructure.dependencies import get_showtimes_use_case

router = APIRouter(prefix="/showtimes", tags=["showtimes"])

@router.get(
    "/",
    response_model=List[ShowtimeResponse],
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_showtimes(
    request: GetShowtimesRequest,
    use_case: GetShowtimesUseCase = Depends(get_showtimes_use_case)
) -> List[ShowtimeResponse]:
    """
    Retrieve showtimes for a specific theater and date.
    
    Returns a list of screenings with movie and theater information.
    """
    try:
        showtimes = await use_case.execute(
            theater_id=request.theater_id,
            date=request.date
        )
        return showtimes
    except TheaterNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

**Step 3**: Wire up dependencies in `src/marquise/infrastructure/dependencies.py`

```python
# src/marquise/infrastructure/dependencies.py
from typing import Annotated
from fastapi import Depends
from marquise.interface_adapters.repositories.mongo_screening_repository import MongoScreeningRepository
from marquise.interface_adapters.repositories.mongo_movie_repository import MongoMovieRepository
from marquise.application.use_cases import (
    GetShowtimesUseCase,
    CreateScreeningUseCase,
    # ... other use cases
)

# Singleton repositories (in production use proper DI container)
_screening_repo: Optional[MongoScreeningRepository] = None
_movie_repo: Optional[MongoMovieRepository] = None

def get_screening_repository() -> ScreeningRepository:
    global _screening_repo
    if _screening_repo is None:
        # Initialize with MongoDB connection from config
        _screening_repo = MongoScreeningRepository()
    return _screening_repo

def get_movie_repository() -> MovieRepository:
    global _movie_repo
    if _movie_repo is None:
        _movie_repo = MongoMovieRepository()
    return _movie_repo

def get_showtimes_use_case(
    screening_repo: ScreeningRepository = Depends(get_screening_repository),
    movie_repo: MovieRepository = Depends(get_movie_repository)
) -> GetShowtimesUseCase:
    from marquise.application.use_cases.get_showtimes import GetShowtimesUseCase
    return GetShowtimesUseCase(
        screening_repository=screening_repo,
        movie_repository=movie_repo
    )
```

**Step 4**: Register routes in `src/marquise/infrastructure/fastapi/app.py`

```python
# src/marquise/infrastructure/fastapi/app.py
from fastapi import FastAPI
from .routes import showtimes, movies, theaters

def create_app() -> FastAPI:
    app = FastAPI(
        title="Marquise API",
        description="Movie showtimes aggregator for Montreal",
        version="0.1.0"
    )
    
    # Include routers
    app.include_router(showtimes.router)
    app.include_router(movies.router)
    app.include_router(theaters.router)
    
    return app

# For direct running
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
```

### 7.4 Error Handling Standards

- **Domain exceptions**: Convert to `HTTPException` in routes or a middleware
- **Validation errors**: FastAPI handles automatically (422)
- **Not found**: 404 with `{"detail": "message"}`
- **Bad request**: 400 with `{"detail": "message"}`
- **Conflict**: 409 for duplicate resources
- **Server error**: 500 with generic message, log details internally

```python
# Define custom domain exceptions in src/marquise/domain/exceptions.py
class DomainException(Exception):
    """Base domain exception."""
    pass

class TheaterNotFoundError(DomainException):
    """Raised when theater doesn't exist."""
    pass

class InvalidScreeningTimeError(DomainException):
    """Raised when screening time is invalid."""
    pass
```

## 8. Data Layer - MongoDB with Clean Architecture

### 8.1 Repository Pattern - The Core Abstraction

**Repository Interface** (defined in application layer):
```python
# src/marquise/application/repositories/screening_repository.py
from abc import ABC, abstractmethod
from marquise.domain.entities import Screening
from datetime import datetime
from typing import List, Optional

class ScreeningRepository(ABC):
    """Abstract repository for screening data persistence."""
    
    @abstractmethod
    async def save(self, screening: Screening) -> Screening:
        """Save a screening. Returns saved screening with ID."""
        pass
    
    @abstractmethod
    async def find_by_id(self, screening_id: str) -> Optional[Screening]:
        """Find screening by ID."""
        pass
    
    @abstractmethod
    async def find_by_theater_and_date_range(
        self,
        theater_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Screening]:
        """Find all screenings for a theater within date range."""
        pass
    
    @abstractmethod
    async def delete(self, screening_id: str) -> bool:
        """Delete screening by ID. Returns True if deleted."""
        pass
```

### 8.2 Interface Adapter Implementation

**MongoDB Implementation** (in interface_adapters layer):

```python
# src/marquise/interface_adapters/repositories/mongo_screening_repository.py
from typing import Optional, List
from datetime import datetime
from pymongo import AsyncMongoClient
from marquise.application.repositories import ScreeningRepository
from marquise.domain.entities import Screening
from marquise.domain.value_objects import ScreeningId, TheaterId, Showtime
import logging
```

### 8.3 Swapping Databases - Demonstration of Clean Architecture

To swap MongoDB for PostgreSQL:

1. Create new repository in `src/marquise/interface_adapters/repositories/postgres_screening_repository.py`
2. Implement same `ScreeningRepository` interface
3. Change dependency injection in `src/marquise/infrastructure/dependencies.py`
4. **Zero changes to domain, application, or infrastructure**

This is the power of clean architecture.

### 8.4 Infrastructure Configuration

```python
# src/marquise/infrastructure/config.py
from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "marquise"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

```python
# src/marquise/infrastructure/database.py
from marquise.infrastructure.config import settings
from pymongo import AsyncMongoClient

_client: Optional[AsyncMongoClient] = None

def get_mongo_client() -> AsyncMongoClient:
    global _client
    if _client is None:
        _client = AsyncMongoClient(settings.mongodb_uri)
    return _client
```

## 9. Testing Strategy

### 9.1 Test Organization

Unit tests mirror the source structure and go in `tests/unit_tests/`. Integration tests, especially for infrastructure layer, go in `tests/integration/`. The `conftest.py` remains at `tests/conftest.py`.

```
tests/
├── conftest.py
├── unit_tests/
│   ├── domain/
│   │   ├── entities/
│   │   ├── value_objects/
│   │   └── services/
│   ├── application/
│   │   ├── use_cases/
│   │   ├── dtos/
│   │   └── repositories/
│   └── infrastructure/
│       └── fastapi/
└── integration/
    └── interface_adapters/
        └── repositories/
```

### 9.2 Testing Types

#### **Domain Tests** (unit tests, no external dependencies)
```python
# tests/unit_tests/domain/entities/test_screening.py
import pytest
from marquise.domain.entities import Screening
from marquise.domain.value_objects import ScreeningId, Showtime, Price

def test_screening_creation() -> None:
    """Test screening can be created with valid data."""
    screening_id = ScreeningId("123")
    showtime = Showtime(datetime(2026, 4, 8, 19, 30))
    price = Price(14.99)
    
    screening = Screening(
        id=screening_id,
        movie_id="movie123",
        theater_id="theater456",
        showtime=showtime,
        price=price
    )
    
    assert screening.id == screening_id
    assert screening.showtime == showtime
    assert screening.price == price

def test_screening_is_available_when_showtime_future() -> None:
    """Test screening availability logic."""
    future_time = datetime.utcnow() + timedelta(hours=1)
    screening = Screening(
        id=ScreeningId("123"),
        movie_id="movie123",
        theater_id="theater456",
        showtime=Showtime(future_time),
        price=Price(14.99)
    )
    assert screening.is_available() is True
    
    past_time = datetime.utcnow() - timedelta(hours=1)
    screening = Screening(
        id=ScreeningId("123"),
        movie_id="movie123",
        theater_id="theater456",
        showtime=Showtime(past_time),
        price=Price(14.99)
    )
    assert screening.is_available() is False
```

#### **Application Tests** (unit tests with mocks)
```python
# tests/unit_tests/application/use_cases/test_get_showtimes.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from marquise.application.use_cases.get_showtimes import GetShowtimesUseCase
from marquise.domain.entities import Screening, Movie
from marquise.domain.value_objects import Showtime, Price

@pytest.mark.asyncio
async def test_get_showtimes_success() -> None:
    """Test get showtimes use case returns screenings."""
    # Arrange
    mock_screening_repo = AsyncMock()
    mock_movie_repo = AsyncMock()
    
    screening = Screening(
        id=ScreeningId("s1"),
        movie_id="m1",
        theater_id="t1",
        showtime=Showtime(datetime(2026, 4, 8, 19, 30)),
        price=Price(14.99)
    )
    mock_screening_repo.find_by_theater_and_date_range.return_value = [screening]
    
    movie = Movie(id="m1", title="Inception", duration_minutes=148)
    mock_movie_repo.find_by_id.return_value = movie
    
    use_case = GetShowtimesUseCase(
        screening_repository=mock_screening_repo,
        movie_repository=mock_movie_repo
    )
    
    # Act
    result = await use_case.execute(theater_id="t1", date=date.today())
    
    # Assert
    assert len(result) == 1
    assert result[0].movie_title == "Inception"
    mock_screening_repo.find_by_theater_and_date_range.assert_called_once()
```

#### **Infrastructure (FastAPI) Tests** (API tests)
```python
# tests/unit_tests/infrastructure/fastapi/test_showtime_routes.py
import pytest
from httpx import AsyncClient
from marquise.infrastructure.fastapi.app import create_app
```

#### **Repository Implementation Tests** (integration tests)
```python
# tests/integration/interface_adapters/repositories/test_mongo_screening_repository.py
import pytest
from marquise.interface_adapters.repositories.mongo_screening_repository import MongoScreeningRepository
from marquise.infrastructure.database import get_mongo_client
from marquise.domain.entities import Screening
from marquise.domain.value_objects import ScreeningId, Showtime, Price
from marquise.application.repositories import ScreeningRepository
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_mongo_repository_save_and_find() -> None:
    """Integration test: save to MongoDB and retrieve."""
    client = get_mongo_client()
    repo = MongoScreeningRepository(client, database_name="marquise_test")
    
    # Ensure clean state
    await repo.collection.delete_many({})
    
    screening = Screening(
        id=None,  # None means new
        movie_id="m1",
        theater_id="t1",
        showtime=Showtime(datetime.utcnow() + timedelta(days=1)),
        price=Price(14.99)
    )
    
    saved = await repo.save(screening)
    assert saved.id is not None
    
    found = await repo.find_by_id(str(saved.id.value))
    assert found is not None
    assert found.id == saved.id
```

### 9.3 Running Tests and Coverage

**Run all tests**:
```bash
uv run pytest tests
```

**Run tests with coverage report**:
```bash
uv run pytest tests/ --cov=marquise.domain --cov=marquise.application --cov=marquise.interface_adapters --cov-report=term-missing
```

This shows:
- Overall coverage percentage
- Which lines are missing in each file

**Generate HTML coverage report**:
```bash
uv run pytest tests/ --cov=marquise.domain --cov=marquise.application --cov=marquise.interface_adapters --cov-report=html
```
Open `htmlcov/index.html` in browser.

**Coverage enforcement**: 100% required for domain, application, interface_adapters. If missing lines exist, **DO NOT COMMIT**.

### 9.4 Test Fixtures

Put reusable fixtures in `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
from datetime import datetime, timedelta
from marquise.domain.entities import Screening, Movie
from marquise.domain.value_objects import ScreeningId, Showtime, Price, MovieId

@pytest.fixture
def sample_screening() -> Screening:
    """Provide a sample screening for tests."""
    return Screening(
        id=ScreeningId("test-screening-1"),
        movie_id="movie-1",
        theater_id="theater-1",
        showtime=Showtime(datetime.utcnow() + timedelta(days=1)),
        price=Price(12.99)
    )

@pytest.fixture
def sample_movie() -> Movie:
    return Movie(
        id=MovieId("movie-1"),
        title="Test Movie",
        duration_minutes=120
    )
```

### 9.5 Async Tests

Always use `pytest-asyncio`:

```bash
uv add --dev pytest-asyncio
```

Mark async tests:

```python
@pytest.mark.asyncio
async def test_async_function() -> None:
    result = await some_async_function()
    assert result is not None
```

### 9.6 Testing Conventions

#### Function-Style Tests (No Classes)

All tests **must** be standalone functions, not methods in a class:

```python
# ✅ Correct - function style
def test_cinema_creation() -> None:
    ...

@pytest.mark.asyncio
async def test_get_showtimes_success() -> None:
    ...

# ❌ Forbidden - class style
class TestCinema:
    def test_creation(self) -> None:
        ...
```

#### Mocking Repositories

Use `unittest.mock.create_autospec` with the repository interface to create mocks that enforce the correct method signatures:

```python
from unittest.mock import AsyncMock, create_autospec

@pytest.mark.asyncio
async def test_use_case_success() -> None:
    mock_repo = create_autospec(CinemaRepository, instance=True)
    mock_repo.find_by_name_and_address.return_value = None
    mock_repo.save.return_value = Cinema(...)

    use_case = CreateCinemaUseCase(cinema_repository=mock_repo)
    response = await use_case.execute(request)

    mock_repo.save.assert_awaited_once()
    mock_repo.find_by_name_and_address.assert_awaited_once_with(
        name="Test Cinema", address="123 Test St"
    )
```

This ensures the mock has the same method signatures as the abstract interface. Use `instance=True` to create an instance-like mock rather than a class-like mock.

Use `assert_awaited_once()` / `assert_awaited_once_with()` for async methods, and `assert_not_awaited()` to verify a method was never called.

## 10. Common Tasks - Step-by-Step Patterns

### 10.1 Adding a New Domain Entity

**Scenario**: Add `Promotion` entity for discount codes.

**Step 1 - Define entity** (`src/marquise/domain/entities/promotion.py`):
```python
from dataclasses import dataclass
from marquise.domain.value_objects import PromotionId, Money, Code
from datetime import datetime
from typing import List

@dataclass(frozen=True)
class Promotion:
    """A promotional discount for screenings."""
    id: PromotionId
    code: Code
    discount_percentage: float
    valid_from: datetime
    valid_until: datetime
    applicable_screening_ids: List[ScreeningId]
    
    def is_valid_for_screening(self, screening_id: ScreeningId) -> bool:
        """Check if promotion applies to given screening and is within date range."""
        now = datetime.utcnow()
        if not (self.valid_from <= now <= self.valid_until):
            return False
        return screening_id in self.applicable_screening_ids
```

**Step 2 - Add value objects if needed** (`src/marquise/domain/value_objects/promotion_id.py`, `code.py`)

**Step 3 - Add repository interface** (`src/marquise/application/repositories/promotion_repository.py`):
```python
from abc import ABC, abstractmethod
from marquise.domain.entities import Promotion
from marquise.domain.value_objects import PromotionId
from typing import Optional, List

class PromotionRepository(ABC):
    @abstractmethod
    async def save(self, promotion: Promotion) -> Promotion:
        pass
    
    @abstractmethod
    async def find_by_code(self, code: str) -> Optional[Promotion]:
        pass
    
    @abstractmethod
    async def find_valid_promotions_for_screening(
        self, screening_id: ScreeningId
    ) -> List[Promotion]:
        pass
```

**Step 4 - Write domain tests immediately** (`tests/unit_tests/domain/entities/test_promotion.py`)

**Step 5 - Implement use case** (`src/marquise/application/use_cases/validate_promotion.py`)

**Step 6 - Implement repository in interface_adapters** (`src/marquise/interface_adapters/repositories/mongo_promotion_repository.py`)

**Step 7 - Add API endpoint** (`src/marquise/infrastructure/fastapi/routes/promotions.py`)

**Step 8 - Write API and integration tests**

**Step 9**: Format, lint, test, commit

### 10.2 Adding a New Use Case

**Scenario**: Add `ApplyPromotionUseCase` to validate and apply discount.

**Step 1 - Create DTOs** (`src/marquise/application/dtos/`):
```python
from pydantic import BaseModel
from datetime import date

class ApplyPromotionRequest(BaseModel):
    screening_id: str
    promotion_code: str
```

**Step 2 - Define use case** (`src/marquise/application/use_cases/apply_promotion.py`):
```python
from marquise.application.repositories import PromotionRepository, ScreeningRepository
from marquise.domain.entities import Screening, Promotion
from marquise.domain.value_objects import Money
from marquise.application.dtos import DiscountedPriceOutputDTO
```

class ApplyPromotionUseCase:
    def __init__(
        self, 
        promotion_repo: PromotionRepository, 
        screening_repo: ScreeningRepository
    ) -> None:
        self.promotion_repo = promotion_repo
        self.screening_repo = screening_repo
    
    async def execute(self, screening_id: str, promotion_code: str) -> DiscountedPriceOutputDTO:
        """Apply promotion to screening and return discounted price."""
        # Fetch domain entities from repositories
        screening = await self.screening_repo.find_by_id(screening_id)
        if not screening:
            raise ValueError("Screening not found")
        
        promotion = await self.promotion_repo.find_by_code(promotion_code)
        if not promotion:
            raise ValueError("Invalid promotion code")
        
        # Business logic: validate and calculate discount
        if not promotion.is_valid_for_screening(screening.id):
            raise ValueError("Promotion not valid for this screening")
        
        discounted_value = screening.price.value * (1 - promotion.discount_percentage / 100)
        
        # Map domain entity data to output DTO
        return DiscountedPriceOutputDTO(
            screening_id=str(screening.id.value),
            original_price=screening.price.value,
            discounted_price=discounted_value,
            savings=screening.price.value - discounted_value,
            promotion_code=promotion.code.value
        )
```

**Step 3 - Write domain tests** (`tests/unit_tests/application/use_cases/test_apply_promotion.py`)

**Step 4 - Wire in dependencies** (`src/marquise/infrastructure/dependencies.py`)

**Step 5 - Add API route** (`src/marquise/infrastructure/fastapi/routes/promotions.py`)

**Step 6**: Format, lint, test, commit

### 10.3 Adding a New API Endpoint

**Scenario**: Add POST `/promotions/validate` endpoint.

**Step 1 - Ensure use case exists** (see 10.2 above)

**Step 2 - Create route** (`src/marquise/infrastructure/fastapi/routes/promotions.py`):
```python
from fastapi import APIRouter, Depends, HTTPException, status
from marquise.application.use_cases import ApplyPromotionUseCase
from marquise.application.dtos.requests import ApplyPromotionRequest
from marquise.application.dtos.responses import DiscountedPriceResponse
```

**Step 3**: Add mock for this route in `tests/unit_tests/infrastructure/fastapi/test_promotion_routes.py`

**Step 4**: Format, lint, test, commit

## 11. Pitfalls to Avoid

### 11.1 Architecture Violations

**Forbidden**:
- Importing infrastructure classes in domain or application
- Using database client directly in routes (must go through repository)
- Putting business logic in routes or repository implementations
- Creating circular dependencies between layers
- Using `Any` type without justification

**If you catch yourself doing any of these, STOP and refactor.**

### 11.2 Skipping Quality Gates

**Never**:
- Commit code that doesn't pass `uv run ruff format .`
- Commit code that doesn't pass `uv run ruff check --fix`
- Commit code with failing tests
- Commit code with less than 100% coverage in core layers

Infrastructure may have lower coverage but still must pass linting and have some test coverage.

### 11.3 Overly Large Changes

**AGENTS SPECIFIC**: Minimize work per session. Do one focused task at a time.

**Good task examples**:
- Add `Promotion` entity with tests (only)
- Add `ApplyPromotionUseCase` with tests (only)
- Add POST `/promotions/validate` endpoint with tests (only)
- Refactor `Screening` validation logic (only)
- Fix coverage gaps in `Movie` entity tests (only)

**Bad task examples**:
- "Build the entire promotions feature" (too broad, spans domain, application, interface)
- "Refactor all repositories" (too many files)
- "Fix all lint errors" (could be many, but if few it's ok)

**Rule**: If your task involves >5 files or touches >2 layers, split it.

### 11.4 Poor Naming and Documentation

- Variable names: descriptive but concise (`screening_repository`, not `scr_repo`)
- Function names: action-oriented (`get_upcoming_showtimes`, not `showtimes_data`)
- Class names: nouns (`ScreeningService`, not `ManageScreenings`)
- File names: snake_case matching contents (`screening_repository.py`, `get_showtimes.py`)
- Document **why** something is done, not what code does (the code shows what)
- Docstrings required on all public classes, methods, functions

### 11.5 Database Leaks

**Never**:
- Return Pydantic models or dicts from repositories - return domain entities or value objects
- Use MongoDB field names (`_id`) in domain layer - use domain IDs (`ScreeningId`)
- Put query logic in use cases - keep it in repositories
- Mix ORM/driver specific types in domain - convert to domain types immediately

## 12. Commands Reference

**Format code**:
```bash
uv run ruff format .
```

**Fix lint errors**:
```bash
uv run ruff check --fix
```

**Run tests**:
```bash
uv run pytest tests
```

**Run tests with coverage**:
```bash
uv run pytest tests/ --cov=marquise.domain --cov=marquise.application --cov=marquise.interface_adapters --cov-report=term-missing
```

**Open HTML coverage report**:
```bash
uv run pytest tests/ --cov=domain --cov=application --cov=interface_adapters --cov-report=html
# Then open htmlcov/index.html in browser
```

**Add dependency**:
```bash
uv add fastapi
uv add --dev pytest-asyncio
uv lock
```

**Sync dependencies** (after pyproject.toml changes):
```bash
uv sync
```

**Run development server** (once implemented):
```bash
uv run python -m marquise.infrastructure.fastapi.app
# or
uv run uvicorn marquise.infrastructure.fastapi.app:create_app --reload
```

**Check Python version**:
```bash
uv run python --version
# Should be Python 3.13.x
```

## 13. Process Guidelines

### 13.1 Branch Naming

- `feature/short-description` (e.g., `feature/add-promotions`, `feature/theater-search`)
- `fix/issue-description` (e.g., `fix/missing-showtime-validation`)
- `refactor/simplify-repository-interface`
- `docs/update-agents-md`

### 13.2 Commit Messages

Format: `type(scope): concise description`

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

Examples:
- `feat(domain): add Promotion entity with validation logic`
- `feat(application): implement ApplyPromotionUseCase`
- `feat(api): add POST /promotions/validate endpoint`
- `test(domain): add coverage for Screening.is_available`
- `fix(api): correct HTTP 400 response format in get_showtimes`
- `refactor(repo): simplify MongoScreeningRepository interface`

### 13.3 Pull Request Process

1. Ensure branch is up-to-date with main (`git pull origin main --rebase`)
2. Run all quality gates: `uv run ruff format .`, `uv run ruff check --fix`, `uv run pytest tests/ --cov=marquise.domain --cov=marquise.application --cov=marquise.interface_adapters`
3. Check coverage - 100% for core layers required
4. Create PR with clear description: what changed, why, how to test
5. Reference any related issues
6. Self-review before requesting review

### 13.4 Work Incrementally

**Workflow**: 
1. Identify smallest meaningful change
2. Implement ONLY that change
3. Write tests for it
4. Format, lint, test
5. Commit with clear message
6. Repeat for next change

**Example**: Adding promotions feature should be broken into:
- Commit 1: Add `Promotion` entity and tests
- Commit 2: Add `PromotionRepository` interface
- Commit 3: Add `ApplyPromotionUseCase` and tests
- Commit 4: Add `MongoPromotionRepository` implementation and integration tests
- Commit 5: Add API endpoint and API tests

**Never** mix unrelated changes in one commit/PR.

## 14. Additional Resources

- **Clean Architecture**: Robert C. Martin's book (Uncle Bob)
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Pydantic**: https://docs.pydantic.dev/
- **pytest**: https://docs.pytest.org/
- **pytest-asyncio**: https://pytest-asyncio.readthedocs.io/
- **Ruff**: https://docs.astral.sh/ruff/
- **uv**: https://github.com/astral-sh/uv

## 15. Questions or Clarifications

If any instruction in this document is unclear or appears contradictory:

1. First, search this document for related sections
2. Ask in project Discord/Slack (link to be added)
3. If urgent, make a decision that preserves clean architecture and code quality, then document your reasoning in code comments and PR description

**Remember**: Clean architecture and test coverage are non-negotiable. When in doubt, err on the side of better separation, more tests, and smaller changes.

---

**Last Updated**: 2026-04-07  
**Maintained By**: Marquise Development Team  
**Review Cycle**: Quarterly or with major architectural changes
