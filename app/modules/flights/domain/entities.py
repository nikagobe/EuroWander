from dataclasses import dataclass, field


@dataclass
class FlightLeg:
    """A single flight leg (one departure → one arrival)."""

    flight_number: str
    airline: str
    departure_airport: str        # IATA code, e.g. "CDG"
    arrival_airport: str          # IATA code, e.g. "BCN"
    departure_time: str           # "2026-06-15 10:15"
    arrival_time: str
    duration_minutes: int
    # Optional enrichment fields from SerpApi
    airline_logo: str = ""
    airplane: str = ""
    departure_airport_name: str = ""
    arrival_airport_name: str = ""
    travel_class: str = "Economy"
    legroom: str = ""
    is_overnight: bool = False
    # Coordinates enriched from airports collection after search
    departure_lat: float | None = None
    departure_lng: float | None = None
    arrival_lat: float | None = None
    arrival_lng: float | None = None
    # City info enriched from countries collection after search
    departure_city_name: str | None = None
    departure_city_freebase_id: str | None = None
    arrival_city_name: str | None = None
    arrival_city_freebase_id: str | None = None


@dataclass
class FlightOffer:
    """
    A complete flight offer that may consist of multiple legs (stops).
    Pure domain model — no MongoDB or FastAPI awareness.
    """

    price: float
    currency: str
    total_duration_minutes: int
    legs: list[FlightLeg] = field(default_factory=list)
    stops: int = 0
    airline_logo: str = ""
    booking_token: str = ""
    source: str = ""          # e.g. "serpapi" or "fake"

    # ── Trip-level summary (first leg → last leg) ─────────────────────────────

    @property
    def departure_airport(self) -> str:
        return self.legs[0].departure_airport if self.legs else ""

    @property
    def departure_airport_name(self) -> str:
        return self.legs[0].departure_airport_name if self.legs else ""

    @property
    def departure_city_name(self) -> str | None:
        return self.legs[0].departure_city_name if self.legs else None

    @property
    def arrival_airport(self) -> str:
        return self.legs[-1].arrival_airport if self.legs else ""

    @property
    def arrival_airport_name(self) -> str:
        return self.legs[-1].arrival_airport_name if self.legs else ""

    @property
    def arrival_city_name(self) -> str | None:
        return self.legs[-1].arrival_city_name if self.legs else None

    @property
    def departure_time(self) -> str:
        return self.legs[0].departure_time if self.legs else ""

    @property
    def arrival_time(self) -> str:
        return self.legs[-1].arrival_time if self.legs else ""

