from dataclasses import dataclass, field


@dataclass
class HotelDestination:
    """
    A Booking.com destination result from the autocomplete API.
    Pure domain model — no MongoDB or FastAPI awareness.
    """

    dest_id: str            # Booking.com internal destination ID (e.g. "-2602512")
    city_name: str          # City name (e.g. "Manchester")
    label: str              # Full label (e.g. "Manchester, Greater Manchester, United Kingdom")


@dataclass
class HotelOffer:
    """
    A single hotel result from Booking.com search.
    Pure domain model — no MongoDB or FastAPI awareness.
    """

    hotel_id: int                   # Booking.com property ID
    name: str                       # Hotel name
    latitude: float
    longitude: float
    photo_url: str                  # Main photo (square thumbnail)
    stars: int                      # Star rating (propertyClass: 0–5)
    review_score: float             # e.g. 9.0
    review_score_word: str          # e.g. "Superb"
    review_count: int
    price_total: float              # Gross total price for the stay
    price_per_night: float          # Gross price per night
    price_excluded: float           # Taxes & charges (excluded from gross)
    currency: str                   # e.g. "EUR", "INR"
    checkin_from: str               # e.g. "14:00"
    checkout_until: str             # e.g. "12:00"
    country_code: str               # e.g. "in", "gb"


@dataclass
class HotelRoomHighlight:
    """A single room highlight/amenity."""

    name: str
    icon: str


@dataclass
class HotelRoom:
    """Room type information extracted from hotel details."""

    room_id: str
    description: str
    photos: list[str] = field(default_factory=list)             # High-res URLs
    highlights: list[HotelRoomHighlight] = field(default_factory=list)
    bed_configurations: list[str] = field(default_factory=list) # e.g. ["2 single beds"]
    room_surface_m2: float = 0.0


@dataclass
class HotelDetails:
    """
    Detailed hotel information from the getHotelDetails endpoint.
    Pure domain model — no MongoDB or FastAPI awareness.
    """

    hotel_id: int
    name: str
    url: str                                        # Booking.com URL
    description: str                                # Hotel description text
    latitude: float
    longitude: float
    address: str
    city: str
    district: str
    country: str
    country_code: str
    zip_code: str
    accommodation_type: str                         # e.g. "Hotels"
    stars: int                                      # Star rating (0–5)
    review_score: float                             # e.g. 9.4
    review_score_word: str                          # e.g. "Wonderful"
    review_count: int
    currency: str
    price_per_night: float                          # Gross amount per night
    price_total: float                              # All-inclusive total
    price_excluded: float                           # Taxes & charges
    available_rooms: int
    breakfast_included: bool
    checkin_from: str                               # e.g. "15:00"
    checkin_until: str                              # e.g. "00:00"
    checkout_from: str                              # e.g. "00:00"
    checkout_until: str                             # e.g. "12:00"
    distance_to_center_km: float                   # Distance to city center
    facilities: list[str] = field(default_factory=list)         # e.g. ["Free WiFi", "Pool"]
    photos: list[str] = field(default_factory=list)             # High-res photo URLs
    rooms: list[HotelRoom] = field(default_factory=list)


