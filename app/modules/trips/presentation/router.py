from fastapi import APIRouter, Depends, Query, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database.client import get_db
from app.modules.buses.domain.entities import BusOffer, BusSegment
from app.modules.finances.application.services import FinanceService
from app.modules.finances.infrastructure.repositories import MongoExpenseRepository
from app.modules.flights.domain.entities import FlightLeg, FlightOffer
from app.modules.flights.infrastructure.booking_client import FakeBookingClient, SerpApiBookingClient
from app.modules.trips.application.booking_service import TripBookingService
from app.modules.trips.application.services import TripService
from app.modules.trips.domain.entities import SavedAttraction, SavedHotel, SavedRestaurant
from app.modules.trips.infrastructure.repositories import MongoTripRepository
from app.modules.trips.presentation.schemas import (
    AddMemberRequest,
    AttractionInput,
    BookingLinkResponse,
    BusJourneyInput,
    CreateTripRequest,
    FlightOfferInput,
    HotelInput,
    MarkAttractionPaidRequest,
    MarkBusPaidRequest,
    MarkFlightPaidRequest,
    MarkHotelPaidRequest,
    MarkRestaurantPaidRequest,
    RescheduleItemRequest,
    RestaurantInput,
    TripMemberResponse,
    TripResponse,
)
from app.modules.users.domain.entities import User
from app.modules.users.application.services import UserService
from app.modules.users.infrastructure.repositories import MongoUserRepository
from app.modules.users.presentation.router import get_current_user

router = APIRouter(prefix="/trips", tags=["trips"])


# ── Dependency factories ──────────────────────────────────────────────────────

def get_trip_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> TripService:
    repo = MongoTripRepository(db["trips"])
    return TripService(repo)


def get_user_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> UserService:
    repo = MongoUserRepository(db["users"])
    return UserService(repo)


def get_booking_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> TripBookingService:
    repo = MongoTripRepository(db["trips"])
    provider = (
        SerpApiBookingClient(settings.serpapi_key)
        if settings.serpapi_key
        else FakeBookingClient()
    )
    return TripBookingService(repo, provider)


def get_finance_service(db: AsyncIOMotorDatabase = Depends(get_db)) -> FinanceService:
    repo = MongoExpenseRepository(db["expenses"])
    return FinanceService(repo)


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
        creator_first_name=current_user.first_name,
        creator_last_name=current_user.last_name,
        forked_from_template_id=req.forked_from_template_id,
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
    user_service: UserService = Depends(get_user_service),
) -> TripResponse:
    """Add a user to the trip.  Only the trip master can call this endpoint."""
    # Resolve the invitee so we can snapshot their name
    invitee = await user_service.get_current_user(req.user_id)
    trip = await service.add_member(
        trip_id=trip_id,
        requester_id=current_user.id,
        new_user_id=req.user_id,
        first_name=invitee.first_name,
        last_name=invitee.last_name,
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


# ── Flight payment endpoints ──────────────────────────────────────────────────

@router.patch(
    "/{trip_id}/flights/{flight_type}/payment",
    response_model=TripResponse,
)
async def mark_flight_paid(
    trip_id: str,
    flight_type: str,
    req: MarkFlightPaidRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Mark a flight ticket (outbound or return) as purchased.

    - **flight_type**: `outbound` or `return`
    - Records the actual price paid, who paid, and which members share the cost.
    - Automatically creates/updates an expense in the finances module so it
      shows up in the Tricount-style balance calculation.
    """
    if flight_type not in ("outbound", "return"):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="flight_type must be 'outbound' or 'return'.")

    trip = await service.mark_flight_paid(
        trip_id=trip_id,
        requester_id=current_user.id,
        flight_type=flight_type,
        actual_paid_amount=req.actual_paid_amount,
        paid_currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
    )

    # Determine the flight snapshot so we can build a meaningful expense name
    flight = trip.outbound_flight if flight_type == "outbound" else trip.return_flight
    first_leg = flight.legs[0] if flight.legs else None
    label = (
        f"{first_leg.flight_number} ({flight_type})"
        if first_leg
        else f"Flight ticket ({flight_type})"
    )

    # Upsert the auto-expense so it appears in the finances module
    await finance_service.upsert_ticket_expense(
        trip_id=trip_id,
        name=label,
        amount=req.actual_paid_amount,
        currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
        source_ref=flight.flight_id,
    )

    return TripResponse.from_entity(trip)


@router.delete(
    "/{trip_id}/flights/{flight_type}/payment",
    response_model=TripResponse,
)
async def unmark_flight_paid(
    trip_id: str,
    flight_type: str,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Clear the payment info from a flight ticket (mark as unpaid).
    Also removes the corresponding auto-generated expense from finances.
    """
    if flight_type not in ("outbound", "return"):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="flight_type must be 'outbound' or 'return'.")

    # Get current trip to retrieve flight_id before clearing
    current_trip = await service.get_trip(trip_id, current_user.id)
    flight = current_trip.outbound_flight if flight_type == "outbound" else current_trip.return_flight

    trip = await service.unmark_flight_paid(
        trip_id=trip_id,
        requester_id=current_user.id,
        flight_type=flight_type,
    )

    # Remove the auto-expense if it exists
    existing = await finance_service._repo.get_by_source_ref(trip_id, flight.flight_id)
    if existing:
        await finance_service.delete_expense(existing.id, trip_id)

    return TripResponse.from_entity(trip)


# ── Bus payment endpoints ─────────────────────────────────────────────────────

@router.patch("/{trip_id}/bus/payment", response_model=TripResponse)
async def mark_bus_paid(
    trip_id: str,
    req: MarkBusPaidRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Mark the trip's bus journey ticket as purchased.

    - Records the actual price paid, who paid, and which members share the cost.
    - Automatically creates/updates an expense in the finances module.
    - Returns 400 if the trip has no bus journey.
    """
    trip = await service.mark_bus_paid(
        trip_id=trip_id,
        requester_id=current_user.id,
        actual_paid_amount=req.actual_paid_amount,
        paid_currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
    )

    bus = trip.bus_journey  # guaranteed non-None after mark_bus_paid succeeds
    label = f"Bus {bus.dep_name} → {bus.arr_name}"  # type: ignore[union-attr]
    source_ref = bus.journey_id or f"bus-{trip_id}"  # type: ignore[union-attr]

    await finance_service.upsert_ticket_expense(
        trip_id=trip_id,
        name=label,
        amount=req.actual_paid_amount,
        currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
        source_ref=source_ref,
    )

    return TripResponse.from_entity(trip)


@router.delete("/{trip_id}/bus/payment", response_model=TripResponse)
async def unmark_bus_paid(
    trip_id: str,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Clear the payment info from the bus journey ticket (mark as unpaid).
    Also removes the corresponding auto-generated expense from finances.
    Returns 400 if the trip has no bus journey.
    """
    current_trip = await service.get_trip(trip_id, current_user.id)
    if current_trip.bus_journey:
        source_ref = current_trip.bus_journey.journey_id or f"bus-{trip_id}"
        existing = await finance_service._repo.get_by_source_ref(trip_id, source_ref)
        if existing:
            await finance_service.delete_expense(existing.id, trip_id)

    trip = await service.unmark_bus_paid(
        trip_id=trip_id,
        requester_id=current_user.id,
    )
    return TripResponse.from_entity(trip)


# ── Hotel endpoints ───────────────────────────────────────────────────────────

def _input_to_saved_hotel(inp: HotelInput) -> SavedHotel:
    """Convert the client-supplied HotelInput into a domain SavedHotel."""
    return SavedHotel(
        hotel_id=inp.hotel_id,
        name=inp.name,
        city=inp.city,
        address=inp.address,
        latitude=inp.latitude,
        longitude=inp.longitude,
        photo_url=inp.photo_url,
        stars=inp.stars,
        review_score=inp.review_score,
        review_score_word=inp.review_score_word,
        checkin_date=inp.checkin_date,
        checkout_date=inp.checkout_date,
        price_per_night=inp.price_per_night,
        price_total=inp.price_total,
        currency=inp.currency,
        booking_url=inp.booking_url,
    )


@router.post("/{trip_id}/hotels", response_model=TripResponse)
async def add_hotel_to_trip(
    trip_id: str,
    req: HotelInput,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    """
    Add a hotel to the trip.

    Send the hotel data as received from `/hotels/search` or `/hotels/details`.
    Multiple hotels can be saved (e.g. one per city in a multi-city trip).
    Returns 409 if the same hotel_id is already saved.
    """
    hotel = _input_to_saved_hotel(req)
    trip = await service.add_hotel(
        trip_id=trip_id,
        requester_id=current_user.id,
        hotel=hotel,
    )
    return TripResponse.from_entity(trip)


@router.delete("/{trip_id}/hotels/{hotel_id}", response_model=TripResponse)
async def remove_hotel_from_trip(
    trip_id: str,
    hotel_id: int,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Remove a specific hotel from the trip by its Booking.com hotel_id.
    Also removes the corresponding auto-generated expense from finances if it exists.
    Returns 400 if the hotel is not found in this trip.
    """
    source_ref = f"hotel-{hotel_id}"
    existing = await finance_service._repo.get_by_source_ref(trip_id, source_ref)
    if existing:
        await finance_service.delete_expense(existing.id, trip_id)

    trip = await service.remove_hotel(
        trip_id=trip_id,
        requester_id=current_user.id,
        hotel_id=hotel_id,
    )
    return TripResponse.from_entity(trip)


@router.get("/{trip_id}/hotels/{hotel_id}/booking-link", response_model=BookingLinkResponse)
async def get_hotel_booking_link(
    trip_id: str,
    hotel_id: int,
    adults: int = Query(1, ge=1, description="Number of adults"),
    rooms: int = Query(1, ge=1, description="Number of rooms"),
    children: int = Query(0, ge=0, description="Number of children"),
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> BookingLinkResponse:
    """
    Generate a direct Booking.com URL for a specific saved hotel,
    pre-filled with check-in/check-out dates and guest parameters.

    Returns 400 if the hotel is not found in this trip or has no booking URL.
    """
    from fastapi import HTTPException

    trip = await service.get_trip(trip_id, current_user.id)
    hotel = trip.find_hotel(hotel_id)
    if hotel is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hotel {hotel_id} not found in this trip.",
        )
    base_url = hotel.booking_url
    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hotel has no booking URL available.",
        )

    # Strip trailing query string from the base URL if present
    if "?" in base_url:
        base_url = base_url.split("?")[0]

    params = (
        f"?checkin={hotel.checkin_date}"
        f"&checkout={hotel.checkout_date}"
        f"&group_adults={adults}"
        f"&req_adults={adults}"
        f"&no_rooms={rooms}"
        f"&group_children={children}"
        f"&req_children={children}"
    )

    return BookingLinkResponse(booking_url=f"{base_url}{params}")


# ── Hotel payment endpoints ───────────────────────────────────────────────────

@router.patch("/{trip_id}/hotels/{hotel_id}/payment", response_model=TripResponse)
async def mark_hotel_paid(
    trip_id: str,
    hotel_id: int,
    req: MarkHotelPaidRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Mark a specific hotel as booked/paid.

    - Records the actual price paid, who paid, and which members share the cost.
    - Automatically creates/updates an expense in the finances module.
    - Returns 400 if the hotel is not found in this trip.
    """
    trip = await service.mark_hotel_paid(
        trip_id=trip_id,
        requester_id=current_user.id,
        hotel_id=hotel_id,
        actual_paid_amount=req.actual_paid_amount,
        paid_currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
    )

    hotel = trip.find_hotel(hotel_id)
    label = f"Hotel: {hotel.name}"  # type: ignore[union-attr]
    source_ref = f"hotel-{hotel_id}"

    await finance_service.upsert_ticket_expense(
        trip_id=trip_id,
        name=label,
        amount=req.actual_paid_amount,
        currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
        source_ref=source_ref,
    )

    return TripResponse.from_entity(trip)


@router.delete("/{trip_id}/hotels/{hotel_id}/payment", response_model=TripResponse)
async def unmark_hotel_paid(
    trip_id: str,
    hotel_id: int,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Clear the payment info from a specific hotel (mark as unpaid).
    Also removes the corresponding auto-generated expense from finances.
    Returns 400 if the hotel is not found in this trip.
    """
    source_ref = f"hotel-{hotel_id}"
    existing = await finance_service._repo.get_by_source_ref(trip_id, source_ref)
    if existing:
        await finance_service.delete_expense(existing.id, trip_id)

    trip = await service.unmark_hotel_paid(
        trip_id=trip_id,
        requester_id=current_user.id,
        hotel_id=hotel_id,
    )
    return TripResponse.from_entity(trip)


# ── Attraction endpoints ──────────────────────────────────────────────────────


def _input_to_saved_attraction(inp: AttractionInput) -> SavedAttraction:
    """Convert the client-supplied AttractionInput into a domain SavedAttraction."""
    return SavedAttraction(
        location_id=inp.location_id,
        name=inp.name,
        category=inp.category,
        photo_url=inp.photo_url,
        latitude=inp.latitude,
        longitude=inp.longitude,
        address=inp.address,
        rating=inp.rating,
        num_reviews=inp.num_reviews,
        ticket_price=inp.ticket_price,
        day_date=inp.day_date,
        time_slot=inp.time_slot,
    )


@router.post("/{trip_id}/attractions", response_model=TripResponse)
async def add_attraction_to_trip(
    trip_id: str,
    req: AttractionInput,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    """
    Add an attraction to the trip.

    Send the attraction data as received from `/attractions/search` or
    `/attractions/details`, plus a `day_date` and `time_slot` for schedule
    placement.  The attraction will appear as an auto-item in the trip schedule
    and can later be marked as paid for expense tracking.

    Returns 409 if the same location_id is already saved.

    **Flutter flow:**
    1. User views attraction detail
    2. Taps "Add to trip" → picks day + time slot
    3. Attraction appears in trip detail AND in the schedule
    """
    attraction = _input_to_saved_attraction(req)
    trip = await service.add_attraction(
        trip_id=trip_id,
        requester_id=current_user.id,
        attraction=attraction,
    )
    return TripResponse.from_entity(trip)


@router.delete("/{trip_id}/attractions/{location_id}", response_model=TripResponse)
async def remove_attraction_from_trip(
    trip_id: str,
    location_id: str,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Remove a specific attraction from the trip by its TripAdvisor location_id.
    Also removes the corresponding auto-generated expense from finances if it exists.
    Returns 400 if the attraction is not found in this trip.
    """
    source_ref = f"attraction-{location_id}"
    existing = await finance_service._repo.get_by_source_ref(trip_id, source_ref)
    if existing:
        await finance_service.delete_expense(existing.id, trip_id)

    trip = await service.remove_attraction(
        trip_id=trip_id,
        requester_id=current_user.id,
        location_id=location_id,
    )
    return TripResponse.from_entity(trip)


# ── Attraction payment endpoints ──────────────────────────────────────────────


@router.patch("/{trip_id}/attractions/{location_id}/payment", response_model=TripResponse)
async def mark_attraction_paid(
    trip_id: str,
    location_id: str,
    req: MarkAttractionPaidRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Mark a specific attraction as paid (e.g. entrance tickets purchased).

    - Records the actual price paid, who paid, and which members share the cost.
    - Automatically creates/updates an expense in the finances module.
    - Returns 400 if the attraction is not found in this trip.
    """
    trip = await service.mark_attraction_paid(
        trip_id=trip_id,
        requester_id=current_user.id,
        location_id=location_id,
        actual_paid_amount=req.actual_paid_amount,
        paid_currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
    )

    attraction = trip.find_attraction(location_id)
    label = f"Attraction: {attraction.name}"  # type: ignore[union-attr]
    source_ref = f"attraction-{location_id}"

    await finance_service.upsert_ticket_expense(
        trip_id=trip_id,
        name=label,
        amount=req.actual_paid_amount,
        currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
        source_ref=source_ref,
    )

    return TripResponse.from_entity(trip)


@router.delete("/{trip_id}/attractions/{location_id}/payment", response_model=TripResponse)
async def unmark_attraction_paid(
    trip_id: str,
    location_id: str,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Clear the payment info from a specific attraction (mark as unpaid).
    Also removes the corresponding auto-generated expense from finances.
    Returns 400 if the attraction is not found in this trip.
    """
    source_ref = f"attraction-{location_id}"
    existing = await finance_service._repo.get_by_source_ref(trip_id, source_ref)
    if existing:
        await finance_service.delete_expense(existing.id, trip_id)

    trip = await service.unmark_attraction_paid(
        trip_id=trip_id,
        requester_id=current_user.id,
        location_id=location_id,
    )
    return TripResponse.from_entity(trip)


# ── Attraction schedule (drag-and-drop) ───────────────────────────────────────


@router.patch("/{trip_id}/attractions/{location_id}", response_model=TripResponse)
async def reschedule_attraction(
    trip_id: str,
    location_id: str,
    req: RescheduleItemRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    """
    Move an attraction to a different day and/or time slot.

    Use this for drag-and-drop rescheduling in the schedule view.
    At least one of `day_date` or `time_slot` must be provided.

    - **day_date**: new date in YYYY-MM-DD format
    - **time_slot**: `morning` | `midday` | `evening` | `night`

    Returns 400 if the attraction is not found or no fields are provided.
    """
    trip = await service.reschedule_attraction(
        trip_id=trip_id,
        requester_id=current_user.id,
        location_id=location_id,
        day_date=req.day_date,
        time_slot=req.time_slot,
    )
    return TripResponse.from_entity(trip)


# ── Restaurant endpoints ──────────────────────────────────────────────────────


def _input_to_saved_restaurant(inp: RestaurantInput) -> SavedRestaurant:
    """Convert the client-supplied RestaurantInput into a domain SavedRestaurant."""
    return SavedRestaurant(
        location_id=inp.location_id,
        name=inp.name,
        cuisine=inp.cuisine,
        photo_url=inp.photo_url,
        latitude=inp.latitude,
        longitude=inp.longitude,
        address=inp.address,
        rating=inp.rating,
        num_reviews=inp.num_reviews,
        price_level=inp.price_level,
        day_date=inp.day_date,
        time_slot=inp.time_slot,
    )


@router.post("/{trip_id}/restaurants", response_model=TripResponse)
async def add_restaurant_to_trip(
    trip_id: str,
    req: RestaurantInput,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    """
    Add a restaurant to the trip.

    Send the restaurant data as received from `/restaurants/search` or
    `/restaurants/details`, plus a `day_date` and `time_slot` for schedule
    placement.  The restaurant will appear as an auto-item in the trip schedule
    and can later be marked as paid for expense tracking.

    Returns 409 if the same location_id is already saved.

    **Flutter flow:**
    1. User views restaurant detail
    2. Taps "Add to trip" → picks day + time slot
    3. Restaurant appears in trip detail AND in the schedule
    """
    restaurant = _input_to_saved_restaurant(req)
    trip = await service.add_restaurant(
        trip_id=trip_id,
        requester_id=current_user.id,
        restaurant=restaurant,
    )
    return TripResponse.from_entity(trip)


@router.delete("/{trip_id}/restaurants/{location_id}", response_model=TripResponse)
async def remove_restaurant_from_trip(
    trip_id: str,
    location_id: str,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Remove a specific restaurant from the trip by its TripAdvisor location_id.
    Also removes the corresponding auto-generated expense from finances if it exists.
    Returns 400 if the restaurant is not found in this trip.
    """
    source_ref = f"restaurant-{location_id}"
    existing = await finance_service._repo.get_by_source_ref(trip_id, source_ref)
    if existing:
        await finance_service.delete_expense(existing.id, trip_id)

    trip = await service.remove_restaurant(
        trip_id=trip_id,
        requester_id=current_user.id,
        location_id=location_id,
    )
    return TripResponse.from_entity(trip)


# ── Restaurant payment endpoints ──────────────────────────────────────────────


@router.patch("/{trip_id}/restaurants/{location_id}/payment", response_model=TripResponse)
async def mark_restaurant_paid(
    trip_id: str,
    location_id: str,
    req: MarkRestaurantPaidRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Mark a specific restaurant as paid (e.g. meal bill settled).

    - Records the actual price paid, who paid, and which members share the cost.
    - Automatically creates/updates an expense in the finances module.
    - Returns 400 if the restaurant is not found in this trip.
    """
    trip = await service.mark_restaurant_paid(
        trip_id=trip_id,
        requester_id=current_user.id,
        location_id=location_id,
        actual_paid_amount=req.actual_paid_amount,
        paid_currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
    )

    restaurant = trip.find_restaurant(location_id)
    label = f"Restaurant: {restaurant.name}"  # type: ignore[union-attr]
    source_ref = f"restaurant-{location_id}"

    await finance_service.upsert_ticket_expense(
        trip_id=trip_id,
        name=label,
        amount=req.actual_paid_amount,
        currency=req.currency,
        paid_by=req.paid_by,
        eligible_member_ids=req.eligible_member_ids,
        source_ref=source_ref,
    )

    return TripResponse.from_entity(trip)


@router.delete("/{trip_id}/restaurants/{location_id}/payment", response_model=TripResponse)
async def unmark_restaurant_paid(
    trip_id: str,
    location_id: str,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
    finance_service: FinanceService = Depends(get_finance_service),
) -> TripResponse:
    """
    Clear the payment info from a specific restaurant (mark as unpaid).
    Also removes the corresponding auto-generated expense from finances.
    Returns 400 if the restaurant is not found in this trip.
    """
    source_ref = f"restaurant-{location_id}"
    existing = await finance_service._repo.get_by_source_ref(trip_id, source_ref)
    if existing:
        await finance_service.delete_expense(existing.id, trip_id)

    trip = await service.unmark_restaurant_paid(
        trip_id=trip_id,
        requester_id=current_user.id,
        location_id=location_id,
    )
    return TripResponse.from_entity(trip)


# ── Restaurant schedule (drag-and-drop) ───────────────────────────────────────


@router.patch("/{trip_id}/restaurants/{location_id}", response_model=TripResponse)
async def reschedule_restaurant(
    trip_id: str,
    location_id: str,
    req: RescheduleItemRequest,
    current_user: User = Depends(get_current_user),
    service: TripService = Depends(get_trip_service),
) -> TripResponse:
    """
    Move a restaurant to a different day and/or time slot.

    Use this for drag-and-drop rescheduling in the schedule view.
    At least one of `day_date` or `time_slot` must be provided.

    - **day_date**: new date in YYYY-MM-DD format
    - **time_slot**: `morning` | `midday` | `evening` | `night`

    Returns 400 if the restaurant is not found or no fields are provided.
    """
    trip = await service.reschedule_restaurant(
        trip_id=trip_id,
        requester_id=current_user.id,
        location_id=location_id,
        day_date=req.day_date,
        time_slot=req.time_slot,
    )
    return TripResponse.from_entity(trip)


