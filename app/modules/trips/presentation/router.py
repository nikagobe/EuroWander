from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database.client import get_db
from app.modules.buses.domain.entities import BusOffer, BusSegment
from app.modules.flights.domain.entities import FlightLeg, FlightOffer
from app.modules.flights.infrastructure.booking_client import FakeBookingClient, SerpApiBookingClient
from app.modules.trips.application.booking_service import TripBookingService
from app.modules.trips.application.services import TripService
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.trips.presentation.schemas import (
    AddMemberRequest,
    BookingLinkResponse,
    BusJourneyInput,
    CreateTripRequest,
    FlightOfferInput,
    TripMemberResponse,
    TripResponse,
)
from app.modules.users.domain.entities import User
from app.modules.users.presentation.router import get_current_user

router = APIRouter(prefix="/trips", tags=["trips"])


# ── Dependency factories ──────────────────────────────────────────────────────

def get_trip_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> TripService:
    repo = MongoTripRepository(db["trips"])
    return TripService(repo)


def get_booking_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> TripBookingService:
    repo = MongoTripRepository(db["trips"])
    provider = (
        SerpApiBookingClient(settings.serpapi_key)
        if settings.serpapi_key
        else FakeBookingClient()
    )
    return TripBookingService(repo, provider)


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


def _input_to_bus_offer(inp: BusJourneyInput) -> BusOffer:
    """Convert the client-supplied BusJourneyInput into a domain BusOffer."""
    segments = [
        BusSegment(
            dep_name=s.dep_name,
            arr_name=s.arr_name,
            dep_time=s.dep_time,
            arr_time=s.arr_time,
            product_type=s.product_type,
            product=s.product,
        )
        for s in inp.segments
    ]
    return BusOffer(
        dep_name=inp.dep_name,
        arr_name=inp.arr_name,
        dep_time=inp.dep_time,
        arr_time=inp.arr_time,
        duration=inp.duration,
        duration_minutes=inp.duration_minutes,
        changeovers=inp.changeovers,
        price=inp.price,
        currency=inp.currency,
        deeplink=inp.deeplink,
        additional_info=inp.additional_info,
        segments=segments,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=TripResponse, status_code=status.HTTP_201_CREATED)
async def create_trip(
    req: CreateTripRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    """
    Create a new trip by selecting an outbound and a return flight,
    plus an optional inter-city bus journey.
    Send `bus_journey: null` (or omit it) if no bus was chosen.
    """
    trip = await service.create_trip(
        user_id=current_user.id,
        outbound_offer=_input_to_offer(req.outbound_flight),
        return_offer=_input_to_offer(req.return_flight),
        name=req.name,
        bus_offer=_input_to_bus_offer(req.bus_journey) if req.bus_journey else None,
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


@router.get("/{trip_id}/booking-link", response_model=BookingLinkResponse)
async def get_booking_link(
    trip_id: str,
    flight: str = Query("outbound", pattern="^(outbound|return)$"),
    current_user: User = Depends(get_current_user),
    service: TripBookingService = Depends(get_booking_service),
) -> BookingLinkResponse:
    """
    Generate a direct vendor booking URL for a saved trip's flight.

    - **flight**: which flight to book — `outbound` (default) or `return`

    Internally re-calls SerpApi with the stored `booking_token`, picks the
    cheapest booking option, then follows Google's redirect to extract the
    final purchasable link.
    """
    booking_url = await service.generate_booking_link(
        trip_id=trip_id,
        user_id=current_user.id,
        flight=flight,
    )
    return BookingLinkResponse(booking_url=booking_url)


# ── Member endpoints ──────────────────────────────────────────────────────────

@router.get("/{trip_id}/members", response_model=list[TripMemberResponse])
async def list_trip_members(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> list[TripMemberResponse]:
    """Return all members of the trip (master + invited members).
    Caller must be an existing member."""
    trip = await service.get_trip(trip_id, current_user.id)
    return [TripMemberResponse.from_entity(m) for m in trip.members]


@router.post(
    "/{trip_id}/members",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_trip_member(
    trip_id: str,
    req: AddMemberRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    """Add a user to the trip.  Only the trip master can call this endpoint."""
    trip = await service.add_member(
        trip_id=trip_id,
        requester_id=current_user.id,
        new_user_id=req.user_id,
    )
    return TripResponse.from_entity(trip)


@router.delete("/{trip_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_trip_member(
    trip_id: str,
    member_user_id: str,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> None:
    """Remove a member from the trip.
    The master can remove anyone; a member can remove themselves (leave)."""
    await service.remove_member(
        trip_id=trip_id,
        requester_id=current_user.id,
        target_user_id=member_user_id,
    )


