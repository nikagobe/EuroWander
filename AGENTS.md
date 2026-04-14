# AGENTS.md - AI Developer Guidelines for EuroWander

**Project Context:** EuroWander is a Flutter-driven travel planning backend for flight/hotel/transport search and itinerary management. Built with FastAPI, MongoDB (Motor), and Domain-Driven Design principles.

## Architecture Principles (Read ARCHITECTURE.md First)

Before coding any feature:
1. **Domain-Driven Design is Non-Negotiable:** Business logic NEVER lives in routers/repositories. Structure follows `app/modules/[feature]/{domain,application,infrastructure,presentation}/`.
2. **Layer Separation:**
   - `domain/`: Pure Python classes (entities.py) and interfaces (interfaces.py). No framework imports.
   - `application/`: Services orchestrating domain logic and repositories. No FastAPI/Pydantic.
   - `infrastructure/`: Motor async queries, external API clients. Technical concerns only.
   - `presentation/`: FastAPI routers (router.py), Pydantic schemas (schemas.py). Thin response mappers only.
3. **Never** put DB logic in routers, business logic in repositories, or framework code in domain.

## Tech Stack Requirements

- **Python 3.12+** with full type hints on all functions and class methods
- **FastAPI** for async HTTP; use `Depends()` for injection, not manual instantiation
- **Motor** for MongoDB (async driver). No blocking pymongo. Never use `.result()` on coroutines.
- **Pydantic v2** for schemas/validation. Use `ConfigDict(json_schema_extra=...)` for Flutter-specific docs.
- **No blocking calls** anywhere. Every I/O operation must be `async/await`.

## Feature Development Workflow

### 1. Read Current Feature Context
```bash
# Always check what we're building this sprint
cat PROJECT_FEATURES.md  # Understand Phase 1, 2, 3, etc.
```

### 2. Module Scaffolding
```python
# app/modules/flights/domain/entities.py
from dataclasses import dataclass

@dataclass
class Flight:
    """Pure domain model - no MongoDB/FastAPI awareness."""
    origin: str
    destination: str
    departure_time: datetime
    
# app/modules/flights/domain/interfaces.py
from abc import ABC, abstractmethod

class FlightRepository(ABC):
    @abstractmethod
    async def find_by_route(self, origin: str, dest: str) -> list[Flight]: ...
```

### 3. Service Layer (Orchestration)
```python
# app/modules/flights/application/services.py
class FlightService:
    def __init__(self, repo: FlightRepository):
        self.repo = repo
    
    async def search_flights(self, origin: str, dest: str) -> list[Flight]:
        # Business logic here, NOT DB queries
        flights = await self.repo.find_by_route(origin, dest)
        return sorted(flights, key=lambda f: f.price)  # Example: rank by price
```

### 4. Repository Implementation
```python
# app/modules/flights/infrastructure/repositories.py
from motor.motor_asyncio import AsyncIOMotorCollection

class MongoFlightRepository(FlightRepository):
    def __init__(self, collection: AsyncIOMotorCollection):
        self.collection = collection
    
    async def find_by_route(self, origin: str, dest: str) -> list[Flight]:
        cursor = self.collection.find({"origin": origin, "destination": dest})
        docs = await cursor.to_list(length=None)
        return [Flight(**doc) for doc in docs]  # Map to domain entity
```

### 5. FastAPI Router
```python
# app/modules/flights/presentation/router.py
from fastapi import APIRouter, Depends
from .schemas import FlightSearchRequest

router = APIRouter(prefix="/flights", tags=["flights"])

@router.get("/search")
async def search_flights(
    req: FlightSearchRequest,
    service: FlightService = Depends(get_flight_service)
) -> list[FlightResponse]:
    flights = await service.search_flights(req.origin, req.destination)
    return [FlightResponse.from_entity(f) for f in flights]
```

## Critical Patterns & Conventions

### Dependency Injection
Always use FastAPI's `Depends()`:
```python
def get_flight_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> FlightService:
    repo = MongoFlightRepository(db["flights"])
    return FlightService(repo)
```

### Motor Async Operations
```python
# ✅ CORRECT
result = await collection.find_one({"_id": id})

# ❌ WRONG - Never use sync pymongo or .result()
result = collection.find_one({"_id": id})  # Blocks event loop!
```

### Pydantic for Flutter Optimization
```python
from pydantic import BaseModel, ConfigDict

class FlightResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"origin": "LHR", "destination": "CDG", "price": 89.99}
        }
    )
    origin: str
    destination: str
    price: float
```

### Testing Integration Patterns
- Mock `FlightRepository` ABC in tests; never mock Motor directly
- Services are unit-testable (inject mock repos); routers are integration-tested (use test database)
- Example: `@pytest.fixture async def mock_repo(): return AsyncMock(spec=FlightRepository)`

## External API Integration Points

Currently planned (see PROJECT_FEATURES.md Phase 2-3):
- **SerpApi:** Parse Google Flights data (Phase 2)
- **Booking.com (RapidAPI):** Hotel search (Phase 3)
- **Google Places API:** POI discovery (Phase 4)

Pattern for external clients:
```python
# app/modules/flights/infrastructure/clients.py
class SerpApiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def search_flights(self, origin: str, dest: str) -> dict:
        # Use aiohttp or httpx for async HTTP
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://api.serpapi.com/search?...")
            return resp.json()
```

## Common Mistakes to Avoid

1. ❌ DB logic in `presentation/router.py` → Move to `infrastructure/repositories.py`
2. ❌ Business logic in `infrastructure/` → Move to `application/services.py`
3. ❌ Sync MongoDB calls (`.result()`, `.find()` without await) → Always use Motor async
4. ❌ Hardcoding API keys in code → Use environment variables + Pydantic `Settings`
5. ❌ Returning raw MongoDB documents to frontend → Map via Pydantic schemas
6. ❌ Type hints only on public methods → Add to ALL functions and class methods

## Debugging & Development Commands

```bash
# Run FastAPI with reload (development)
uvicorn app.main:app --reload

# Run tests with pytest
pytest tests/ -v --asyncio-mode=auto

# Check type hints
mypy app/

# Format code
black app/
```

## File Organization Reference

```
app/
├── main.py                          # FastAPI app entry point
├── config.py                        # Settings, environment loading
├── modules/
│   ├── flights/
│   │   ├── domain/
│   │   │   ├── entities.py         # Flight class (pure Python)
│   │   │   └── interfaces.py       # FlightRepository ABC
│   │   ├── application/
│   │   │   └── services.py         # FlightService
│   │   ├── infrastructure/
│   │   │   ├── repositories.py     # MongoFlightRepository
│   │   │   └── clients.py          # External API clients (SerpApi, etc.)
│   │   └── presentation/
│   │       ├── router.py           # FastAPI routes
│   │       └── schemas.py          # Pydantic request/response models
│   └── [other_features]/           # Same structure for users, trips, hotels, etc.
└── database/
    └── client.py                   # Motor connection setup
```

## Before Starting a Task

- [ ] Read `ARCHITECTURE.md` (foundational)
- [ ] Read `PROJECT_FEATURES.md` (current phase context)
- [ ] Check existing module structure in `app/modules/` for patterns
- [ ] Verify no blocking I/O or sync MongoDB calls
- [ ] Confirm all functions have Python 3.12+ type hints
- [ ] Ensure repositories are injected, not hardcoded

