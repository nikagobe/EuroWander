# ARCHITECTURE.md - EuroWander Backend

## 1. Core Principles
- **Domain-Driven Design (DDD):** Logic is isolated from frameworks.
- **Object-Oriented (OOP):** Use classes, encapsulation, and inheritance.
- **Interface-Based:** Depend on Abstract Base Classes (ABCs), not implementations.
- **Async-First:** All I/O operations must use `async/await`.

## 2. Technology Stack
- **Language:** Python 3.12+
- **Framework:** FastAPI
- **Database:** MongoDB (using `Motor` for async driver)
- **Validation:** Pydantic v2
- **Frontend Awareness:** Optimized for Flutter consumption (Clean JSON).

## 3. Directory Structure (Mandatory)
Each feature lives in `app/modules/[name]/`:
- `domain/`: Pure logic. `entities.py` (Classes), `interfaces.py` (ABCs).
- `application/`: Orchestration. `services.py` (Use cases).
- `infrastructure/`: Technical details. `repositories.py` (Mongo logic), `clients.py` (External APIs).
- `presentation/`: API entry points. `router.py`, `schemas.py` (Pydantic models).

## 4. Design Patterns
- **Repository Pattern:** To hide MongoDB details from business logic.
- **Dependency Injection:** Inject repositories into services via FastAPI `Depends`.