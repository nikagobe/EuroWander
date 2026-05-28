from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database.client import get_db
from app.modules.buses.application.services import BusService
from app.modules.buses.domain.interfaces import BusSearchProvider
from app.modules.buses.infrastructure.fake_client import FakeBusClient
from app.modules.buses.infrastructure.flixbus_client import FlixbusClient
from app.modules.buses.presentation.schemas import BusOfferResponse, BusSearchRequest

router = APIRouter(prefix="/buses", tags=["buses"])


def get_bus_provider() -> BusSearchProvider:
    """
    Returns the real Flixbus/RapidAPI client when RAPIDAPI_KEY is configured,
    or the fake client otherwise.
    """
    if settings.rapidapi_key:
        return FlixbusClient(api_key=settings.rapidapi_key)
    return FakeBusClient()


def get_bus_service(
    provider: BusSearchProvider = Depends(get_bus_provider),
) -> BusService:
    return BusService(provider)


async def _resolve_flixbus_id(freebase_id: str, db: AsyncIOMotorDatabase) -> str:
    """
    Look up a city's flixbus_id from the countries collection using its freebase_id.
    Raises 404 if not found or if the city has no Flixbus coverage.
    """
    doc = await db["countries"].find_one(
        {"major_cities.freebase_id": freebase_id},
        {"major_cities.$": 1},
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"City with freebase_id '{freebase_id}' not found in major cities.",
        )
    city = doc["major_cities"][0]
    flixbus_id: str | None = city.get("flixbus_id")
    if not flixbus_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"City '{city.get('name')}' has no Flixbus coverage "
                f"(flixbus_id not available)."
            ),
        )
    return flixbus_id


@router.post("/search", response_model=list[BusOfferResponse])
async def search_buses(
    req: BusSearchRequest,
    service: BusService = Depends(get_bus_service),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[BusOfferResponse]:
    """
    Search for Flixbus journeys between two cities.

    - `origin_freebase_id` / `destination_freebase_id`: freebase IDs from the
      city/countries collection (same IDs used for flights).
    - `date`: departure date in **YYYY-MM-DD** format.
    - Results are sorted by price (cheapest first).

    Uses real RapidAPI/Flixbus when `RAPIDAPI_KEY` env var is set; fake data otherwise.
    """
    # Convert YYYY-MM-DD → DD.MM.YYYY (Flixbus format)
    year, month, day = req.date.split("-")
    flixbus_date = f"{day}.{month}.{year}"

    from_flixbus_id = await _resolve_flixbus_id(req.origin_freebase_id, db)
    to_flixbus_id = await _resolve_flixbus_id(req.destination_freebase_id, db)

    offers = await service.search_buses(
        from_id=from_flixbus_id,
        to_id=to_flixbus_id,
        date=flixbus_date,
        adults=req.adults,
        currency=req.currency,
        limit=req.limit,
    )
    return [BusOfferResponse.from_entity(offer) for offer in offers]

