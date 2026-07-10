import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Force logging to work both locally and in Lambda containers.
# Lambda's runtime may pre-configure the root logger, making basicConfig() a no-op.
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if not root_logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(levelname)s\t%(name)s\t%(message)s"))
    root_logger.addHandler(handler)

from app.config import settings
from app.database.client import close_client, get_client
from app.modules.airports.presentation.router import router as airports_router
from app.modules.cities.presentation.router import router as cities_router
from app.modules.countries.presentation.router import router as countries_router
from app.modules.buses.presentation.router import router as buses_router
from app.modules.documents.infrastructure.repositories import MongoDocumentRepository
from app.modules.documents.presentation.router import router as documents_router
from app.modules.finances.infrastructure.repositories import MongoExpenseRepository
from app.modules.finances.presentation.router import router as finances_router
from app.modules.flights.presentation.router import router as flights_router
from app.modules.attractions.presentation.router import router as attractions_router
from app.modules.hotels.presentation.router import router as hotels_router
from app.modules.restaurants.presentation.router import router as restaurants_router
from app.modules.photos.infrastructure.repositories import MongoPhotoRepository
from app.modules.photos.presentation.router import router as photos_router
from app.modules.playlists.infrastructure.repositories import MongoPlaylistRepository, MongoPlaylistReviewRepository
from app.modules.playlists.presentation.router import router as playlists_router
from app.modules.schedule.infrastructure.repositories import MongoScheduleRepository
from app.modules.schedule.presentation.router import router as schedule_router
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.trips.presentation.router import router as trips_router
from app.modules.users.infrastructure.repositories import MongoUserRepository
from app.modules.users.presentation.router import router as users_router

# Detect if running inside AWS Lambda
_IS_LAMBDA = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: verify database connection
    try:
        logger.info("Connecting to MongoDB...")
        client = get_client()
        await client.admin.command("ping")
        logger.info("MongoDB connection OK")
        # Ensure indexes
        db = client[settings.database_name]
        await MongoUserRepository(db["users"]).ensure_indexes()
        await MongoTripRepository(db["trips"]).ensure_indexes()
        await MongoExpenseRepository(db["expenses"]).ensure_indexes()
        await MongoDocumentRepository(db["documents"]).ensure_indexes()
        await MongoPhotoRepository(db["photos"]).ensure_indexes()
        await MongoScheduleRepository(db["schedule_items"]).ensure_indexes()
        await MongoPlaylistRepository(db["playlists"]).ensure_indexes()
        await MongoPlaylistReviewRepository(db["playlist_reviews"]).ensure_indexes()
        logger.info("Indexes ensured")
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise
    yield
    # Shutdown: On Lambda, do NOT close the client — the connection
    # must persist across warm invocations. Lambda destroys the
    # container when it's done. On uvicorn/local, close normally.
    if not _IS_LAMBDA:
        close_client()


app = FastAPI(
    title="EuroWander API",
    description="Travel planning backend for EuroWander Flutter app.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(airports_router, prefix="/api/v1")
app.include_router(cities_router, prefix="/api/v1")
app.include_router(countries_router, prefix="/api/v1")
app.include_router(flights_router, prefix="/api/v1")
app.include_router(hotels_router, prefix="/api/v1")
app.include_router(attractions_router, prefix="/api/v1")
app.include_router(restaurants_router, prefix="/api/v1")
app.include_router(buses_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(trips_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(photos_router, prefix="/api/v1")
app.include_router(finances_router, prefix="/api/v1")
app.include_router(schedule_router, prefix="/api/v1")
app.include_router(playlists_router, prefix="/api/v1")



@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


