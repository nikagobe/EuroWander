"""
Trip domain entities.

A Trip is owned by a user and anchored by two flights:
  - outbound_flight  : the "there" leg
  - return_flight    : the "back" leg

It may also include an optional inter-city bus journey (Flixbus):
  - bus_journey : a SavedBusJourney snapshot, or None if no bus was chosen.

A SavedFlight / SavedBusJourney are value-object snapshots embedded in the
Trip document so the record is self-contained even if provider data changes.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TripStatus(str, Enum):
    PLANNING = "planning"
    BOOKED   = "booked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TripRole(str, Enum):
    MASTER = "master"   # Trip creator / owner — full control
    MEMBER = "member"   # Invited participant — read-only access


@dataclass
class TripMember:
    """Value object representing one participant in a Trip."""
    user_id: str
    role: TripRole
    joined_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SavedFlightLeg:
    """Snapshot of one flight leg stored inside a Trip."""
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


@dataclass
class SavedFlight:
    """A flight offer snapshot embedded in a Trip."""
    flight_id: str
    price: float
    currency: str
    total_duration_minutes: int
    stops: int
    airline_logo: str
    booking_token: str
    legs: list[SavedFlightLeg] = field(default_factory=list)


@dataclass
class SavedBusSegment:
    """Snapshot of one Flixbus segment."""
    dep_name: str
    arr_name: str
    dep_time: str
    arr_time: str
    product_type: str   # "bus" | "train"
    product: str        # "flixbus"


@dataclass
class SavedBusJourney:
    """
    A Flixbus journey snapshot embedded in a Trip.
    Optional — user may not have chosen a bus connection.
    """
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
    segments: list[SavedBusSegment] = field(default_factory=list)


@dataclass
class Trip:
    """Pure domain model — no MongoDB or FastAPI awareness."""
    user_id: str                                 # trip master user_id
    outbound_flight: SavedFlight
    return_flight: SavedFlight
    name: str = ""                               # user-defined trip name
    bus_journey: SavedBusJourney | None = None   # optional inter-city bus
    members: list[TripMember] = field(default_factory=list)
    id: str = ""
    status: TripStatus = TripStatus.PLANNING
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_master(self, user_id: str) -> bool:
        """Return True if *user_id* is the trip master."""
        return self.user_id == user_id

    def has_member(self, user_id: str) -> bool:
        """Return True if *user_id* is already a participant (any role)."""
        return any(m.user_id == user_id for m in self.members)

