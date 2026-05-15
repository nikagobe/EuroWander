from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.client import get_db
from app.modules.countries.application.services import CountryService
from app.modules.countries.domain.entities import Country
from app.modules.countries.infrastructure.repositories import MongoCountryRepository
from app.modules.countries.presentation.schemas import CountryResponse, MajorCityResponse

router = APIRouter(prefix="/countries", tags=["countries"])


def _country_to_response(country: Country) -> CountryResponse:
    return CountryResponse(
        name=country.name,
        neighbors=country.neighbors,
        major_cities=[
            MajorCityResponse(
                name=c.name,
                wikidata_id=c.wikidata_id,
                freebase_id=c.freebase_id,
                description=c.description,
            )
            for c in country.major_cities
        ],
    )


def get_country_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> CountryService:
    repo = MongoCountryRepository(db["countries"])
    return CountryService(repo)


@router.get(
    "/{country_name}",
    response_model=CountryResponse,
    summary="Get country details with neighbors and major cities",
)
async def get_country(
    country_name: str,
    service: CountryService = Depends(get_country_service),
) -> CountryResponse:
    country = await service.get_country(country_name)
    if country is None:
        raise HTTPException(status_code=404, detail=f"Country '{country_name}' not found.")
    return _country_to_response(country)


@router.get(
    "/{country_name}/neighbors-with-cities",
    response_model=list[CountryResponse],
    summary="Get neighboring countries with their major cities (for flight suggestions)",
)
async def get_neighbors_with_cities(
    country_name: str,
    service: CountryService = Depends(get_country_service),
) -> list[CountryResponse]:
    """
    Returns all countries that border `country_name`, each with their top major cities.
    Use this to suggest flight destinations to the user based on their departure country.
    """
    neighbors = await service.get_neighbors_with_cities(country_name)
    if not neighbors:
        # Could be an island nation or unknown country
        country = await service.get_country(country_name)
        if country is None:
            raise HTTPException(status_code=404, detail=f"Country '{country_name}' not found.")
    return [_country_to_response(n) for n in neighbors]

