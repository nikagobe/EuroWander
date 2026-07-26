"""
Trip domain entities.

A Trip is owned by a user and anchored by two flights:
  - outbound_flight  : the "there" leg
  - return_flight    : the "back" leg

It may also include:
  - bus_journey : a SavedBusJourney snapshot, or None if no bus was chosen.
  - hotels      : a list of SavedHotel snapshots (one per city/leg).

A SavedFlight / SavedBusJourney / SavedHotel are value-object snapshots
embedded in the Trip document so the record is self-contained even if
provider data changes.
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
    """Value object representing one participant in a Trip.
    Name fields are snapshotted at invite time so the trip document is self-contained."""
    user_id: str
    role: TripRole
    first_name: str = ""
    last_name: str = ""
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
    # Payment tracking
    is_paid: bool = False
    actual_paid_amount: float | None = None
    paid_currency: str | None = None
    paid_by: str | None = None          # user_id of who paid
    eligible_member_ids: list[str] = field(default_factory=list)  # who shares this cost


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
    journey_id: str = ""             # stable ID built at snapshot time
    # Payment tracking
    is_paid: bool = False
    actual_paid_amount: float | None = None
    paid_currency: str | None = None
    paid_by: str | None = None          # user_id of who paid
    eligible_member_ids: list[str] = field(default_factory=list)


@dataclass
class SavedHotel:
    """
    A Booking.com hotel snapshot embedded in a Trip.
    Optional — user may not have chosen a hotel.
    """
    hotel_id: int                       # Booking.com property ID
    name: str
    city: str
    address: str
    latitude: float
    longitude: float
    photo_url: str                      # Main thumbnail URL
    stars: int
    review_score: float
    review_score_word: str
    checkin_date: str                   # YYYY-MM-DD
    checkout_date: str                  # YYYY-MM-DD
    price_per_night: float
    price_total: float
    currency: str
    booking_url: str = ""               # Booking.com direct URL
    # Payment tracking
    is_paid: bool = False
    actual_paid_amount: float | None = None
    paid_currency: str | None = None
    paid_by: str | None = None          # user_id of who paid
    eligible_member_ids: list[str] = field(default_factory=list)


@dataclass
class SavedAttraction:
    """
    A TripAdvisor attraction snapshot embedded in a Trip.
    Stores enough data for the Flutter trip-detail card, schedule auto-items,
    and expense tracking.
    """
    location_id: str                    # TripAdvisor location ID (unique key)
    name: str
    category: str                       # e.g. "Amusement & Theme Parks"
    photo_url: str
    latitude: float
    longitude: float
    address: str
    rating: float
    num_reviews: int
    ticket_price: str                   # e.g. "Tickets from $107 USD" or ""
    day_date: str                       # YYYY-MM-DD — planned visit date
    time_slot: str                      # morning | midday | evening | night
    # Payment tracking
    is_paid: bool = False
    actual_paid_amount: float | None = None
    paid_currency: str | None = None
    paid_by: str | None = None
    eligible_member_ids: list[str] = field(default_factory=list)


@dataclass
class SavedRestaurant:
    """
    A TripAdvisor restaurant snapshot embedded in a Trip.
    Stores enough data for the Flutter trip-detail card, schedule auto-items,
    and expense tracking.
    """
    location_id: str                    # TripAdvisor location ID (unique key)
    name: str
    cuisine: str                        # e.g. "$$ - $$$ • Japanese • Bar"
    photo_url: str
    latitude: float
    longitude: float
    address: str
    rating: float
    num_reviews: int
    price_level: str                    # "$", "$$ - $$$", "$$$$", ""
    day_date: str                       # YYYY-MM-DD — planned visit date
    time_slot: str                      # morning | midday | evening | night
    # Payment tracking
    is_paid: bool = False
    actual_paid_amount: float | None = None
    paid_currency: str | None = None
    paid_by: str | None = None
    eligible_member_ids: list[str] = field(default_factory=list)


@dataclass
class Trip:
    """Pure domain model — no MongoDB or FastAPI awareness."""
    user_id: str                                 # trip master user_id
    outbound_flight: SavedFlight
    return_flight: SavedFlight
    name: str = ""                               # user-defined trip name
    bus_journey: SavedBusJourney | None = None   # optional inter-city bus
    hotels: list[SavedHotel] = field(default_factory=list)  # multiple hotel bookings
    attractions: list[SavedAttraction] = field(default_factory=list)
    restaurants: list[SavedRestaurant] = field(default_factory=list)
    members: list[TripMember] = field(default_factory=list)
    id: str = ""
    status: TripStatus = TripStatus.PLANNING
    forked_from_template_id: str = ""    # links to source template if forked
    destination_image_filename: str = ""  # Wikimedia Commons filename for thumbnail
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_master(self, user_id: str) -> bool:
        """Return True if *user_id* is the trip master."""
        return self.user_id == user_id

    def has_member(self, user_id: str) -> bool:
        """Return True if *user_id* is already a participant (any role)."""
        return any(m.user_id == user_id for m in self.members)

    def find_hotel(self, hotel_id: int) -> SavedHotel | None:
        """Find a hotel in the list by its Booking.com hotel_id."""
        return next((h for h in self.hotels if h.hotel_id == hotel_id), None)

    def find_attraction(self, location_id: str) -> SavedAttraction | None:
        """Find an attraction by its TripAdvisor location_id."""
        return next((a for a in self.attractions if a.location_id == location_id), None)

    def find_restaurant(self, location_id: str) -> SavedRestaurant | None:
        """Find a restaurant by its TripAdvisor location_id."""
        return next((r for r in self.restaurants if r.location_id == location_id), None)

