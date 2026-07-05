from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.trips.domain.entities import (
    SavedAttraction,
    SavedBusJourney,
    SavedBusSegment,
    SavedFlight,
    SavedFlightLeg,
    SavedHotel,
    SavedRestaurant,
    Trip,
    TripMember,
    TripRole,
    TripStatus,
)


# ── Reusable flight offer input (what the client sends) ──────────────────────

class FlightLegInput(BaseModel):
    flight_number: str
    airline: str
    airline_logo: str = ""
    airplane: str = ""
    departure_airport: str
    departure_airport_name: str = ""
    arrival_airport: str
    arrival_airport_name: str = ""
    departure_time: str          # "2026-06-15 10:15"
    arrival_time: str
    duration_minutes: int
    travel_class: str = "Economy"
    legroom: str = ""
    is_overnight: bool = False


class FlightOfferInput(BaseModel):
    """
    The client sends back the full flight offer it received from the
    /flights/search endpoint. We snapshot it into the trip.
    """
    price: float
    currency: str
    total_duration_minutes: int
    stops: int
    airline_logo: str = ""
    booking_token: str = ""
    legs: list[FlightLegInput]


# ── Bus journey input (optional) ─────────────────────────────────────────────

class BusSegmentInput(BaseModel):
    dep_name: str
    arr_name: str
    dep_time: str
    arr_time: str
    product_type: str = "bus"
    product: str = "flixbus"


class BusJourneyInput(BaseModel):
    """
    The client sends back the full bus offer as returned by /buses/search.
    This is optional — omit or set to null if no bus was chosen.
    """
    dep_name: str
    arr_name: str
    dep_time: str
    arr_time: str
    duration: str
    duration_minutes: int
    changeovers: int
    price: float
    currency: str = "EUR"
    deeplink: str = ""
    additional_info: str = ""
    segments: list[BusSegmentInput] = []


class HotelInput(BaseModel):
    """
    The client sends hotel data from /hotels/search or /hotels/details
    to save it to a trip.
    """
    hotel_id: int
    name: str
    city: str = ""
    address: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    photo_url: str = ""
    stars: int = 0
    review_score: float = 0.0
    review_score_word: str = ""
    checkin_date: str                   # YYYY-MM-DD
    checkout_date: str                  # YYYY-MM-DD
    price_per_night: float
    price_total: float
    currency: str = "EUR"
    booking_url: str = ""


class AttractionInput(BaseModel):
    """
    The client sends attraction data from /attractions/search or /attractions/details
    to save it to a trip.  Must include day_date + time_slot for schedule placement.
    """
    location_id: str
    name: str
    category: str = ""
    photo_url: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    address: str = ""
    rating: float = 0.0
    num_reviews: int = 0
    ticket_price: str = ""
    day_date: str                       # YYYY-MM-DD
    time_slot: str = "morning"          # morning | midday | evening | night

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location_id": "188757",
                "name": "Eiffel Tower",
                "category": "Sights & Landmarks",
                "photo_url": "https://...",
                "latitude": 48.8584,
                "longitude": 2.2945,
                "address": "Champ de Mars, 5 Avenue Anatole France",
                "rating": 4.5,
                "num_reviews": 142000,
                "ticket_price": "Tickets from €26",
                "day_date": "2026-07-28",
                "time_slot": "morning",
            }
        }
    )


class RestaurantInput(BaseModel):
    """
    The client sends restaurant data from /restaurants/search or /restaurants/details
    to save it to a trip.  Must include day_date + time_slot for schedule placement.
    """
    location_id: str
    name: str
    cuisine: str = ""
    photo_url: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    address: str = ""
    rating: float = 0.0
    num_reviews: int = 0
    price_level: str = ""
    day_date: str                       # YYYY-MM-DD
    time_slot: str = "evening"          # morning | midday | evening | night

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location_id": "1234567",
                "name": "Le Jules Verne",
                "cuisine": "$$$$ • French",
                "photo_url": "https://...",
                "latitude": 48.8583,
                "longitude": 2.2944,
                "address": "Eiffel Tower, 2nd floor",
                "rating": 4.0,
                "num_reviews": 3200,
                "price_level": "$$$$",
                "day_date": "2026-07-28",
                "time_slot": "evening",
            }
        }
    )


class CreateTripRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Barcelona Summer Trip",
                "outbound_flight": {
                    "price": 37.0,
                    "currency": "EUR",
                    "total_duration_minutes": 105,
                    "stops": 0,
                    "airline_logo": "https://...",
                    "booking_token": "abc",
                    "legs": [
                        {
                            "flight_number": "FR 3122",
                            "airline": "Ryanair",
                            "departure_airport": "BVA",
                            "departure_airport_name": "Paris Beauvais Airport",
                            "arrival_airport": "BCN",
                            "arrival_airport_name": "Barcelona El Prat",
                            "departure_time": "2026-06-15 10:45",
                            "arrival_time": "2026-06-15 12:30",
                            "duration_minutes": 105,
                        }
                    ],
                },
                "return_flight": {
                    "price": 42.0,
                    "currency": "EUR",
                    "total_duration_minutes": 110,
                    "stops": 0,
                    "airline_logo": "https://...",
                    "booking_token": "xyz",
                    "legs": [
                        {
                            "flight_number": "FR 3123",
                            "airline": "Ryanair",
                            "departure_airport": "BCN",
                            "departure_airport_name": "Barcelona El Prat",
                            "arrival_airport": "BVA",
                            "arrival_airport_name": "Paris Beauvais Airport",
                            "departure_time": "2026-06-22 13:00",
                            "arrival_time": "2026-06-22 14:50",
                            "duration_minutes": 110,
                        }
                    ],
                },
                "bus_journey": {
                    "dep_name": "Berlin central bus station",
                    "arr_name": "Munich central bus station",
                    "dep_time": "2026-06-15T08:00:00.000",
                    "arr_time": "2026-06-15T15:40:00.000",
                    "duration": "07:40",
                    "duration_minutes": 460,
                    "changeovers": 0,
                    "price": 26.99,
                    "currency": "EUR",
                    "deeplink": "https://shop.flixbus.com/...",
                    "additional_info": "",
                    "segments": [],
                },
            }
        }
    )

    outbound_flight: FlightOfferInput
    return_flight: FlightOfferInput
    name: str = ""
    bus_journey: BusJourneyInput | None = None


# ── Response schemas ─────────────────────────────────────────────────────────

class SavedFlightLegResponse(BaseModel):
    flight_number: str
    airline: str
    airline_logo: str
    airplane: str
    departure_airport: str
    departure_airport_name: str
    arrival_airport: str
    arrival_airport_name: str
    departure_time: str
    arrival_time: str
    duration_minutes: int
    travel_class: str
    legroom: str
    is_overnight: bool

    @classmethod
    def from_entity(cls, leg: SavedFlightLeg) -> "SavedFlightLegResponse":
        return cls(**leg.__dict__)


class SavedFlightResponse(BaseModel):
    flight_id: str
    price: float
    currency: str
    total_duration_minutes: int
    stops: int
    airline_logo: str
    booking_token: str
    legs: list[SavedFlightLegResponse]
    is_paid: bool
    actual_paid_amount: float | None
    paid_currency: str | None
    paid_by: str | None
    eligible_member_ids: list[str]

    @classmethod
    def from_entity(cls, f: SavedFlight) -> "SavedFlightResponse":
        return cls(
            flight_id=f.flight_id,
            price=f.price,
            currency=f.currency,
            total_duration_minutes=f.total_duration_minutes,
            stops=f.stops,
            airline_logo=f.airline_logo,
            booking_token=f.booking_token,
            legs=[SavedFlightLegResponse.from_entity(l) for l in f.legs],
            is_paid=f.is_paid,
            actual_paid_amount=f.actual_paid_amount,
            paid_currency=f.paid_currency,
            paid_by=f.paid_by,
            eligible_member_ids=f.eligible_member_ids,
        )


class BusSegmentResponse(BaseModel):
    dep_name: str
    arr_name: str
    dep_time: str
    arr_time: str
    product_type: str
    product: str

    @classmethod
    def from_entity(cls, seg: SavedBusSegment) -> "BusSegmentResponse":
        return cls(**seg.__dict__)


class BusJourneyResponse(BaseModel):
    journey_id: str
    dep_name: str
    arr_name: str
    dep_time: str
    arr_time: str
    duration: str
    duration_minutes: int
    changeovers: int
    price: float
    currency: str
    deeplink: str
    additional_info: str
    segments: list[BusSegmentResponse]
    is_paid: bool
    actual_paid_amount: float | None
    paid_currency: str | None
    paid_by: str | None
    eligible_member_ids: list[str]

    @classmethod
    def from_entity(cls, b: SavedBusJourney) -> "BusJourneyResponse":
        return cls(
            journey_id=b.journey_id,
            dep_name=b.dep_name,
            arr_name=b.arr_name,
            dep_time=b.dep_time,
            arr_time=b.arr_time,
            duration=b.duration,
            duration_minutes=b.duration_minutes,
            changeovers=b.changeovers,
            price=b.price,
            currency=b.currency,
            deeplink=b.deeplink,
            additional_info=b.additional_info,
            segments=[BusSegmentResponse.from_entity(s) for s in b.segments],
            is_paid=b.is_paid,
            actual_paid_amount=b.actual_paid_amount,
            paid_currency=b.paid_currency,
            paid_by=b.paid_by,
            eligible_member_ids=b.eligible_member_ids,
        )


class BookingLinkResponse(BaseModel):
    booking_url: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"booking_url": "https://track.metaconnect.saas.amadeus.com/..."}}
    )


class SavedHotelResponse(BaseModel):
    hotel_id: int
    name: str
    city: str
    address: str
    latitude: float
    longitude: float
    photo_url: str
    stars: int
    review_score: float
    review_score_word: str
    checkin_date: str
    checkout_date: str
    price_per_night: float
    price_total: float
    currency: str
    booking_url: str
    is_paid: bool
    actual_paid_amount: float | None
    paid_currency: str | None
    paid_by: str | None
    eligible_member_ids: list[str]

    @classmethod
    def from_entity(cls, h: SavedHotel) -> "SavedHotelResponse":
        return cls(
            hotel_id=h.hotel_id,
            name=h.name,
            city=h.city,
            address=h.address,
            latitude=h.latitude,
            longitude=h.longitude,
            photo_url=h.photo_url,
            stars=h.stars,
            review_score=h.review_score,
            review_score_word=h.review_score_word,
            checkin_date=h.checkin_date,
            checkout_date=h.checkout_date,
            price_per_night=h.price_per_night,
            price_total=h.price_total,
            currency=h.currency,
            booking_url=h.booking_url,
            is_paid=h.is_paid,
            actual_paid_amount=h.actual_paid_amount,
            paid_currency=h.paid_currency,
            paid_by=h.paid_by,
            eligible_member_ids=h.eligible_member_ids,
        )


class SavedAttractionResponse(BaseModel):
    location_id: str
    name: str
    category: str
    photo_url: str
    latitude: float
    longitude: float
    address: str
    rating: float
    num_reviews: int
    ticket_price: str
    day_date: str
    time_slot: str
    is_paid: bool
    actual_paid_amount: float | None
    paid_currency: str | None
    paid_by: str | None
    eligible_member_ids: list[str]

    @classmethod
    def from_entity(cls, a: SavedAttraction) -> "SavedAttractionResponse":
        return cls(
            location_id=a.location_id,
            name=a.name,
            category=a.category,
            photo_url=a.photo_url,
            latitude=a.latitude,
            longitude=a.longitude,
            address=a.address,
            rating=a.rating,
            num_reviews=a.num_reviews,
            ticket_price=a.ticket_price,
            day_date=a.day_date,
            time_slot=a.time_slot,
            is_paid=a.is_paid,
            actual_paid_amount=a.actual_paid_amount,
            paid_currency=a.paid_currency,
            paid_by=a.paid_by,
            eligible_member_ids=a.eligible_member_ids,
        )


class SavedRestaurantResponse(BaseModel):
    location_id: str
    name: str
    cuisine: str
    photo_url: str
    latitude: float
    longitude: float
    address: str
    rating: float
    num_reviews: int
    price_level: str
    day_date: str
    time_slot: str
    is_paid: bool
    actual_paid_amount: float | None
    paid_currency: str | None
    paid_by: str | None
    eligible_member_ids: list[str]

    @classmethod
    def from_entity(cls, r: SavedRestaurant) -> "SavedRestaurantResponse":
        return cls(
            location_id=r.location_id,
            name=r.name,
            cuisine=r.cuisine,
            photo_url=r.photo_url,
            latitude=r.latitude,
            longitude=r.longitude,
            address=r.address,
            rating=r.rating,
            num_reviews=r.num_reviews,
            price_level=r.price_level,
            day_date=r.day_date,
            time_slot=r.time_slot,
            is_paid=r.is_paid,
            actual_paid_amount=r.actual_paid_amount,
            paid_currency=r.paid_currency,
            paid_by=r.paid_by,
            eligible_member_ids=r.eligible_member_ids,
        )


# ── Member schemas ────────────────────────────────────────────────────────────

class AddMemberRequest(BaseModel):
    user_id: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"user_id": "664abc123def456789012345"}}
    )


class TripMemberResponse(BaseModel):
    user_id: str
    role: TripRole
    first_name: str
    last_name: str
    joined_at: datetime

    @classmethod
    def from_entity(cls, m: TripMember) -> "TripMemberResponse":
        return cls(
            user_id=m.user_id,
            role=m.role,
            first_name=m.first_name,
            last_name=m.last_name,
            joined_at=m.joined_at,
        )


class TripResponse(BaseModel):
    id: str
    user_id: str
    name: str
    status: TripStatus
    members: list[TripMemberResponse]
    outbound_flight: SavedFlightResponse
    return_flight: SavedFlightResponse
    bus_journey: BusJourneyResponse | None
    hotels: list[SavedHotelResponse]
    attractions: list[SavedAttractionResponse]
    restaurants: list[SavedRestaurantResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, trip: Trip) -> "TripResponse":
        return cls(
            id=trip.id,
            user_id=trip.user_id,
            name=trip.name,
            status=trip.status,
            members=[TripMemberResponse.from_entity(m) for m in trip.members],
            outbound_flight=SavedFlightResponse.from_entity(trip.outbound_flight),
            return_flight=SavedFlightResponse.from_entity(trip.return_flight),
            bus_journey=BusJourneyResponse.from_entity(trip.bus_journey) if trip.bus_journey else None,
            hotels=[SavedHotelResponse.from_entity(h) for h in trip.hotels],
            attractions=[SavedAttractionResponse.from_entity(a) for a in trip.attractions],
            restaurants=[SavedRestaurantResponse.from_entity(r) for r in trip.restaurants],
            created_at=trip.created_at,
            updated_at=trip.updated_at,
        )


# ── Flight payment schema ────────────────────────────────────────────────────

class MarkFlightPaidRequest(BaseModel):
    """
    Called when a user marks a flight ticket as bought.
    actual_paid_amount: real price paid (may differ from estimated price).
    paid_by: user_id of the member who paid.
    eligible_member_ids: user_ids of members who share this cost.
    currency: currency of actual_paid_amount (defaults to the flight's currency).
    """
    actual_paid_amount: float
    paid_by: str
    eligible_member_ids: list[str]
    currency: str = "EUR"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "actual_paid_amount": 74.50,
                "currency": "EUR",
                "paid_by": "664abc123def456789012345",
                "eligible_member_ids": ["664abc123def456789012345", "664abc123def456789099999"],
            }
        }
    )


class MarkBusPaidRequest(BaseModel):
    """
    Called when a user marks a bus journey ticket as bought.
    Identical shape to MarkFlightPaidRequest — kept separate for clarity.
    """
    actual_paid_amount: float
    paid_by: str
    eligible_member_ids: list[str]
    currency: str = "EUR"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "actual_paid_amount": 26.99,
                "currency": "EUR",
                "paid_by": "664abc123def456789012345",
                "eligible_member_ids": ["664abc123def456789012345", "664abc123def456789099999"],
            }
        }
    )


class MarkHotelPaidRequest(BaseModel):
    """
    Called when a user marks the hotel as booked/paid.
    """
    actual_paid_amount: float
    paid_by: str
    eligible_member_ids: list[str]
    currency: str = "EUR"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "actual_paid_amount": 450.00,
                "currency": "EUR",
                "paid_by": "664abc123def456789012345",
                "eligible_member_ids": ["664abc123def456789012345", "664abc123def456789099999"],
            }
        }
    )


class MarkAttractionPaidRequest(BaseModel):
    """
    Called when a user marks an attraction ticket/entry as paid.
    """
    actual_paid_amount: float
    paid_by: str
    eligible_member_ids: list[str]
    currency: str = "EUR"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "actual_paid_amount": 26.00,
                "currency": "EUR",
                "paid_by": "664abc123def456789012345",
                "eligible_member_ids": ["664abc123def456789012345", "664abc123def456789099999"],
            }
        }
    )


class MarkRestaurantPaidRequest(BaseModel):
    """
    Called when a user marks a restaurant meal as paid.
    """
    actual_paid_amount: float
    paid_by: str
    eligible_member_ids: list[str]
    currency: str = "EUR"

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "actual_paid_amount": 85.00,
                "currency": "EUR",
                "paid_by": "664abc123def456789012345",
                "eligible_member_ids": ["664abc123def456789012345", "664abc123def456789099999"],
            }
        }
    )


