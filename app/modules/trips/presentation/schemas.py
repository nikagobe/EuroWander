from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.trips.domain.entities import SavedFlight, SavedFlightLeg, Trip, TripStatus


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


class CreateTripRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
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
            }
        }
    )

    outbound_flight: FlightOfferInput
    return_flight: FlightOfferInput


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


class TripResponse(BaseModel):
    id: str
    user_id: str
    status: TripStatus
    outbound_flight: SavedFlightResponse
    return_flight: SavedFlightResponse
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, trip: Trip) -> "TripResponse":
        return cls(
            id=trip.id,
            user_id=trip.user_id,
            status=trip.status,
            outbound_flight=SavedFlightResponse.from_entity(trip.outbound_flight),
            return_flight=SavedFlightResponse.from_entity(trip.return_flight),
            created_at=trip.created_at,
            updated_at=trip.updated_at,
        )

