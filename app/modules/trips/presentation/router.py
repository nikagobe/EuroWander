from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.client import get_db
from app.modules.flights.domain.entities import FlightLeg, FlightOffer
from app.modules.trips.application.services import TripService
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.trips.presentation.schemas import (
    CreateTripRequest,
    FlightOfferInput,
    TripResponse,
)
from app.modules.users.domain.entities import User
from app.modules.users.presentation.router import get_current_user

router = APIRouter(prefix="/trips", tags=["trips"])


# ── Dependency factories ──────────────────────────────────────────────────────

def get_trip_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> TripService:
    repo = MongoTripRepository(db["trips"])
    return TripService(repo)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _input_to_offer(inp: FlightOfferInput) -> FlightOffer:
    """Convert the client-supplied FlightOfferInput into a domain FlightOffer."""
    legs = [
        FlightLeg(
            flight_number=leg.flight_number,
            airline=leg.airline,
            airline_logo=leg.airline_logo,
            airplane=leg.airplane,
            departure_airport=leg.departure_airport,
            departure_airport_name=leg.departure_airport_name,
            arrival_airport=leg.arrival_airport,
            arrival_airport_name=leg.arrival_airport_name,
            departure_time=leg.departure_time,
            arrival_time=leg.arrival_time,
            duration_minutes=leg.duration_minutes,
            travel_class=leg.travel_class,
            legroom=leg.legroom,
            is_overnight=leg.is_overnight,
        )
        for leg in inp.legs
    ]
    return FlightOffer(
        price=inp.price,
        currency=inp.currency,
        total_duration_minutes=inp.total_duration_minutes,
        stops=inp.stops,
        airline_logo=inp.airline_logo,
        booking_token=inp.booking_token,
        legs=legs,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    req: CreateTripRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    """
    Create a new trip by selecting an outbound and a return flight.
    The client sends the full flight offer objects exactly as returned
    by the /flights/search endpoint.
    """
    trip = await service.create_trip(
        user_id=current_user.id,
        outbound_offer=_input_to_offer(req.outbound_flight),
        return_offer=_input_to_offer(req.return_flight),
    )
    return TripResponse.from_entity(trip)


@router.get("", response_model=list[TripResponse])
async def list_trips(
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> list[TripResponse]:
    """Return all trips belonging to the authenticated user, newest first."""
    trips = await service.list_trips(current_user.id)
    return [TripResponse.from_entity(t) for t in trips]


@router.get("/{trip_id}", response_model=TripResponse)
async def get_trip(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    """Fetch a single trip by ID (must belong to the authenticated user)."""
    trip = await service.get_trip(trip_id, current_user.id)
    return TripResponse.from_entity(trip)


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trip(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> None:
    """Delete a trip (must belong to the authenticated user)."""
    await service.delete_trip(trip_id, current_user.id)


