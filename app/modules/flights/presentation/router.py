from fastapi import APIRouter, Depends

from app.config import settings
from app.modules.flights.application.services import FlightService
from app.modules.flights.domain.interfaces import FlightSearchProvider
from app.modules.flights.infrastructure.fake_client import FakeFlightClient
from app.modules.flights.infrastructure.serpapi_client import SerpApiFlightClient
from app.modules.flights.presentation.schemas import FlightOfferResponse, FlightSearchRequest

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


@router.post("/search", response_model=list[FlightOfferResponse])
async def search_flights(
    req: FlightSearchRequest,
    service: FlightService = Depends(get_flight_service),
) -> list[FlightOfferResponse]:
    """
    Search for flights between two IATA airport codes.
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
    return [FlightOfferResponse.from_entity(offer) for offer in offers]

