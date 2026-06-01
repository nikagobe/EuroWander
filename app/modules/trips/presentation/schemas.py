from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.trips.domain.entities import (
    SavedBusJourney,
    SavedBusSegment,
    SavedFlight,
    SavedFlightLeg,
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

    @classmethod
    def from_entity(cls, b: SavedBusJourney) -> "BusJourneyResponse":
        return cls(
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
        )


class BookingLinkResponse(BaseModel):
    booking_url: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"booking_url": "https://track.metaconnect.saas.amadeus.com/..."}}
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
    joined_at: datetime

    @classmethod
    def from_entity(cls, m: TripMember) -> "TripMemberResponse":
        return cls(user_id=m.user_id, role=m.role, joined_at=m.joined_at)


class TripResponse(BaseModel):
    id: str
    user_id: str
    name: str
    status: TripStatus
    members: list[TripMemberResponse]
    outbound_flight: SavedFlightResponse
    return_flight: SavedFlightResponse
    bus_journey: BusJourneyResponse | None
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
            created_at=trip.created_at,
            updated_at=trip.updated_at,
        )
