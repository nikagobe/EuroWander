from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database.client import get_db
from app.modules.airports.infrastructure.repositories import MongoAirportRepository
from app.modules.countries.infrastructure.repositories import MongoCountryRepository
from app.modules.flights.application.enrichment import enrich_offers_with_coords
from app.modules.flights.application.regional_service import MultiOriginFlightService, RegionalSearchParams
from app.modules.flights.application.services import FlightService
from app.modules.flights.domain.interfaces import FlightSearchProvider
from app.modules.flights.infrastructure.fake_client import FakeFlightClient
from app.modules.flights.infrastructure.serpapi_client import SerpApiFlightClient
from app.modules.flights.presentation.schemas import (
    FlightOfferResponse,
    FlightSearchRequest,
    IataFlightSearchRequest,
    RegionalFlightSearchRequest,
)

router = APIRouter(prefix="/flights", tags=["flights"])


def get_flight_provider() -> FlightSearchProvider:
    """
    Returns the real SerpApi client when a key is configured,
    or the fake client otherwise — no code changes needed to switch.
    """
    if settings.serpapi_key:
        return SerpApiFlightClient(api_key=settings.serpapi_key)
    return FakeFlightClient()


def get_flight_service(
    provider: FlightSearchProvider = Depends(get_flight_provider),
) -> FlightService:
    return FlightService(provider)


def get_regional_flight_service(
    provider: FlightSearchProvider = Depends(get_flight_provider),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> MultiOriginFlightService:
    country_repo = MongoCountryRepository(db["countries"])
    return MultiOriginFlightService(provider=provider, country_repo=country_repo)


@router.post("/search", response_model=list[FlightOfferResponse])
async def search_flights(
    req: FlightSearchRequest,
    service: FlightService = Depends(get_flight_service),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[FlightOfferResponse]:
    """
    Search for flights between two cities (by freebase_id).
    Results are ranked by price (cheapest first).
    Uses SerpApi when `SERPAPI_KEY` env var is set; fake data otherwise.
    """
    offers = await service.search_flights(
        origin=req.origin_id,
        destination=req.destination_id,
        outbound_date=req.outbound_date,
        return_date=req.return_date,
        adults=req.adults,
        limit=req.limit,
    )
    airport_repo = MongoAirportRepository(db["airports"])
    country_repo = MongoCountryRepository(db["countries"])
    offers = await enrich_offers_with_coords(offers, airport_repo, country_repo)
    return [FlightOfferResponse.from_entity(offer) for offer in offers]


@router.post("/regional-search", response_model=list[FlightOfferResponse])
async def regional_search_flights(
    req: RegionalFlightSearchRequest,
    service: MultiOriginFlightService = Depends(get_regional_flight_service),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[FlightOfferResponse]:
    """
    Search return flights from a whole region (origin country + its neighbours)
    to a destination city.

    - Collects all major cities with a freebase_id from the origin country
      and every bordering country.
    - Batches them into groups of ≤ 5 (SerpApi limit) and fires concurrent requests.
    - Returns merged results ranked by price (cheapest first).
    """
    params = RegionalSearchParams(
        origin_country=req.origin_country,
        destination_id=req.destination_id,
        outbound_date=req.outbound_date,
        return_date=req.return_date,
        adults=req.adults,
        limit=req.limit,
    )
    offers = await service.search_from_region(params)
    airport_repo = MongoAirportRepository(db["airports"])
    country_repo = MongoCountryRepository(db["countries"])
    offers = await enrich_offers_with_coords(offers, airport_repo, country_repo)
    return [FlightOfferResponse.from_entity(offer) for offer in offers]


@router.post("/search-by-iata", response_model=list[FlightOfferResponse])
async def search_flights_by_iata(
    req: IataFlightSearchRequest,
    service: FlightService = Depends(get_flight_service),
    db: AsyncIOMotorDatabase = Depends(get_db),
) -> list[FlightOfferResponse]:
    """
    Search for flights using IATA airport codes (e.g. "LHR", "BCN").
    Used by the template fork wizard where routes are defined by IATA pairs.
    SerpApi accepts IATA codes directly as departure_id/arrival_id.
    """
    offers = await service.search_flights(
        origin=req.origin_iata,
        destination=req.destination_iata,
        outbound_date=req.outbound_date,
        return_date=req.return_date,
        adults=req.adults,
        limit=req.limit,
    )
    airport_repo = MongoAirportRepository(db["airports"])
    country_repo = MongoCountryRepository(db["countries"])
    offers = await enrich_offers_with_coords(offers, airport_repo, country_repo)
    return [FlightOfferResponse.from_entity(offer) for offer in offers]
