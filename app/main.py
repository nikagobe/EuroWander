from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.config import settings
from app.database.client import get_client
from app.modules.cities.presentation.router import router as cities_router
from app.modules.countries.presentation.router import router as countries_router
from app.modules.flights.presentation.router import router as flights_router
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.trips.presentation.router import router as trips_router
from app.modules.users.infrastructure.repositories import MongoUserRepository
from app.modules.users.presentation.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: verify database connection
    client = get_client()
    await client.admin.command("ping")
    # Ensure unique index on users.email
    db = client[settings.database_name]
    await MongoUserRepository(db["users"]).ensure_indexes()
    await MongoTripRepository(db["trips"]).ensure_indexes()
    yield
    # Shutdown: close the MongoDB connection
    client.close()


app = FastAPI(
    title="EuroWander API",
    description="Travel planning backend for EuroWander Flutter app.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(cities_router, prefix="/api/v1")
app.include_router(countries_router, prefix="/api/v1")
app.include_router(flights_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(trips_router, prefix="/api/v1")



@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


