"""
Trip domain entities.

A Trip is owned by a user and anchored by two flights:
  - outbound_flight : the "there" leg
  - return_flight   : the "back" leg (always required for a round trip)

A SavedFlight is a snapshot of a FlightOffer at the moment the user picked it.
We store it as a value-object embedded in the Trip document so the trip record
is self-contained even if provider data changes later.

Flight identity key (flight_id):
  "{dep_airport}-{arr_airport}-{departure_date}-{flight_number}"
  Built from the *first* leg of the offer. For multi-leg flights the key still
  uniquely identifies the offer because the first leg departure + number is unique.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TripStatus(str, Enum):
    PLANNING = "planning"
    BOOKED   = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class SavedFlightLeg:
    """Snapshot of one leg stored inside a Trip — no external references."""
    flight_number: str
    airline: str
    airline_logo: str
    airplane: str
    departure_airport: str        # IATA, e.g. "CDG"
    departure_airport_name: str
    arrival_airport: str          # IATA, e.g. "BCN"
    arrival_airport_name: str
    departure_time: str           # "2026-06-15 10:15"
    arrival_time: str
    duration_minutes: int
    travel_class: str
    legroom: str
    is_overnight: bool


@dataclass
class SavedFlight:
    """
    A flight offer snapshot embedded in a Trip.
    `flight_id` is a human-readable stable key built at save time.
    """
    flight_id: str                # "{dep}-{arr}-{date}-{flight_number}"
    price: float
    currency: str
    total_duration_minutes: int
    stops: int
    airline_logo: str
    booking_token: str
    legs: list[SavedFlightLeg] = field(default_factory=list)


@dataclass
class Trip:
    """Pure domain model — no MongoDB or FastAPI awareness."""
    user_id: str
    outbound_flight: SavedFlight
    return_flight: SavedFlight
    id: str = ""
    status: TripStatus = TripStatus.PLANNING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

