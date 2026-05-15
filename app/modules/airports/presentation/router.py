from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.client import get_db
from app.modules.airports.application.services import AirportService
from app.modules.airports.infrastructure.repositories import MongoAirportRepository
from app.modules.airports.presentation.schemas import AirportResponse

router = APIRouter(prefix="/airports", tags=["airports"])


def get_airport_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> AirportService:
    return AirportService(MongoAirportRepository(db["airports"]))


@router.get("/search", response_model=list[AirportResponse])
async def search_airports(
    q: str = Query(..., min_length=1, description="Airport name or IATA code"),
    limit: int = Query(10, ge=1, le=50),
    service: AirportService = Depends(get_airport_service),
) -> list[AirportResponse]:
    """Search airports by name prefix or exact IATA code (e.g. 'CDG', 'Paris')."""
    airports = await service.search(q, limit)
    return [AirportResponse.from_entity(a) for a in airports]


@router.get("/{iata_code}", response_model=AirportResponse)
async def get_airport(
    iata_code: str,
    service: AirportService = Depends(get_airport_service),
) -> AirportResponse:
    """Get a single airport by its IATA code."""
    airport = await service.get_by_iata(iata_code.upper())
    if not airport:
        raise HTTPException(status_code=404, detail=f"Airport '{iata_code}' not found.")
    return AirportResponse.from_entity(airport)


@router.get("/country/{country_code}", response_model=list[AirportResponse])
async def get_airports_by_country(
    country_code: str,
    service: AirportService = Depends(get_airport_service),
) -> list[AirportResponse]:
    """Get all airports for a given ISO country code (e.g. 'FR', 'DE')."""
    airports = await service.get_by_country(country_code.upper())
    return [AirportResponse.from_entity(a) for a in airports]

