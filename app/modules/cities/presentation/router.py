from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.client import get_db
from app.modules.cities.application.services import CityService
from app.modules.cities.infrastructure.repositories import MongoCityRepository
from app.modules.cities.presentation.schemas import CityResponse

router = APIRouter(prefix="/cities", tags=["cities"])


def get_city_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> CityService:
    repo = MongoCityRepository(db["cities"])
    return CityService(repo)


@router.get("/search", response_model=list[CityResponse])
async def search_cities(
    q: str = Query(min_length=1, description="City name to search for"),
    limit: int = Query(default=10, ge=1, le=20, description="Number of results"),
    service: CityService = Depends(get_city_service),
) -> list[CityResponse]:
    cities = await service.search(q, limit)
    return [CityResponse.from_entity(city) for city in cities]

