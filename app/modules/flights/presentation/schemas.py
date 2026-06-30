from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.flights.domain.entities import FlightLeg, FlightOffer


# ── Request ─────────────────────────────────────────────────────────────────

class FlightSearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_id": "/m/05qtj",
                "destination_id": "/m/01f62",
                "outbound_date": "2026-06-15",
                "return_date": None,
                "adults": 1,
                "limit": 10,
            }
        }
    )

    # freebase_id values from the City entity (e.g. "/m/05qtj" for Paris)
    origin_id: str
    destination_id: str
    outbound_date: str        # YYYY-MM-DD
    return_date: str | None = None
    adults: int = Field(default=1, ge=1, le=9, description="Number of adult passengers (1-9)")
    limit: int = 10

    @field_validator("origin_id", "destination_id")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


# ── Regional / Multi-Origin Request ──────────────────────────────────────────

class RegionalFlightSearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_country": "France",
                "destination_id": "/m/01f62",
                "outbound_date": "2026-06-15",
                "return_date": None,
                "adults": 1,
                "limit": 20,
            }
        }
    )

    origin_country: str          # Country name as stored in MongoDB, e.g. "France"
    destination_id: str          # freebase_id of the destination city
    outbound_date: str           # YYYY-MM-DD
    return_date: str | None = None
    adults: int = Field(default=1, ge=1, le=9, description="Number of adult passengers (1-9)")
    limit: int = 20

    @field_validator("destination_id")
    @classmethod
    def strip_destination(cls, v: str) -> str:
        return v.strip()


# ── Response ─────────────────────────────────────────────────────────────────

class FlightLegResponse(BaseModel):
    flight_number: str
    airline: str
    airline_logo: str
    airplane: str
    departure_airport: str          # IATA code
    departure_airport_name: str
    departure_lat: float | None = None
    departure_lng: float | None = None
    departure_city_name: str | None = None
    departure_city_freebase_id: str | None = None
    arrival_airport: str            # IATA code
    arrival_airport_name: str
    arrival_lat: float | None = None
    arrival_lng: float | None = None
    arrival_city_name: str | None = None
    arrival_city_freebase_id: str | None = None
    departure_time: str
    arrival_time: str
    duration_minutes: int
    travel_class: str
    legroom: str
    is_overnight: bool

    @classmethod
    def from_entity(cls, leg: FlightLeg) -> "FlightLegResponse":
        return cls(
            flight_number=leg.flight_number,
            airline=leg.airline,
            airline_logo=leg.airline_logo,
            airplane=leg.airplane,
            departure_airport=leg.departure_airport,
            departure_airport_name=leg.departure_airport_name,
            departure_lat=leg.departure_lat,
            departure_lng=leg.departure_lng,
            departure_city_name=leg.departure_city_name,
            departure_city_freebase_id=leg.departure_city_freebase_id,
            arrival_airport=leg.arrival_airport,
            arrival_airport_name=leg.arrival_airport_name,
            arrival_lat=leg.arrival_lat,
            arrival_lng=leg.arrival_lng,
            arrival_city_name=leg.arrival_city_name,
            arrival_city_freebase_id=leg.arrival_city_freebase_id,
            departure_time=leg.departure_time,
            arrival_time=leg.arrival_time,
            duration_minutes=leg.duration_minutes,
            travel_class=leg.travel_class,
            legroom=leg.legroom,
            is_overnight=leg.is_overnight,
        )


class FlightOfferResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "price": 238.0,
                "price_per_person": 119.0,
                "currency": "EUR",
                "adults": 2,
                "total_duration_minutes": 680,
                "stops": 1,
                "departure_airport": "BSL",
                "departure_airport_name": "EuroAirport Basel-Mulhouse-Freiburg",
                "departure_city_name": "Basel",
                "arrival_airport": "TBS",
                "arrival_airport_name": "Tbilisi International Airport",
                "arrival_city_name": "Tbilisi",
                "departure_time": "2026-06-15 11:45",
                "arrival_time": "2026-06-16 01:05",
                "airline_logo": "https://www.gstatic.com/flights/airline_logos/70px/VF.png",
                "booking_token": "abc123",
                "source": "serpapi",
                "legs": [],
            }
        }
    )

    price: float                    # Total price for all adults
    price_per_person: float         # Price divided among adults
    currency: str
    adults: int                     # Number of passengers the price covers
    total_duration_minutes: int
    stops: int
    # Trip-level summary: origin (first leg) → final destination (last leg)
    departure_airport: str
    departure_airport_name: str
    departure_city_name: str | None = None
    arrival_airport: str
    arrival_airport_name: str
    arrival_city_name: str | None = None
    departure_time: str
    arrival_time: str
    airline_logo: str
    booking_token: str
    source: str
    legs: list[FlightLegResponse]

    @classmethod
    def from_entity(cls, offer: FlightOffer) -> "FlightOfferResponse":
        return cls(
            price=offer.price,
            price_per_person=offer.price_per_person,
            currency=offer.currency,
            adults=offer.adults,
            total_duration_minutes=offer.total_duration_minutes,
            stops=offer.stops,
            departure_airport=offer.departure_airport,
            departure_airport_name=offer.departure_airport_name,
            departure_city_name=offer.departure_city_name,
            arrival_airport=offer.arrival_airport,
            arrival_airport_name=offer.arrival_airport_name,
            arrival_city_name=offer.arrival_city_name,
            departure_time=offer.departure_time,
            arrival_time=offer.arrival_time,
            airline_logo=offer.airline_logo,
            booking_token=offer.booking_token,
            source=offer.source,
            legs=[FlightLegResponse.from_entity(leg) for leg in offer.legs],
        )



