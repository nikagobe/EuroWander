from dataclasses import dataclass, field


@dataclass
class AttractionDestination:
    """
    A city/destination result from TripAdvisor autocomplete (RapidAPI scraper).
    Pure domain model — no MongoDB or FastAPI awareness.
    Used by Flutter to let users pick a city before browsing attractions.
    """

    geo_id: int                     # TripAdvisor geo ID (e.g. 187147 for Paris)
    name: str                       # City name (e.g. "Paris")
    secondary_text: str             # Region/country (e.g. "Ile-de-France, France")
    image_url: str                  # City photo URL (if available)


@dataclass
class Attraction:
    """
    A single attraction from TripAdvisor search results.
    Pure domain model — no MongoDB or FastAPI awareness.
    """

    location_id: str                # TripAdvisor location ID
    name: str                       # Attraction name (without ranking prefix)
    category: str                   # e.g. "Amusement & Theme Parks"
    neighborhood: str               # e.g. "Lake Buena Vista" or ""
    rating: float                   # Bubble rating 1.0–5.0
    num_reviews: int                # Total review count
    photo_url: str                  # Photo URL (resized)
    latitude: float                 # From map pins
    longitude: float                # From map pins
    badge: str                      # e.g. "TRAVELLER_CHOICE", "BEST_OF_BEST", ""
    ticket_price: str               # e.g. "Tickets from $107 USD" or ""
    is_open_now: bool               # Whether attraction is currently open


@dataclass
class PaginatedAttractions:
    """A page of attraction results with pagination metadata."""

    items: list[Attraction]
    current_page: int
    total_pages: int
    total_results: int
    page_size: int


@dataclass
class AttractionPhoto:
    """A single photo for an attraction."""

    url: str
    caption: str
    width: int
    height: int


@dataclass
class AttractionReview:
    """A user review for an attraction."""

    rating: float
    title: str
    text: str
    author: str
    published_date: str
    trip_type: str


@dataclass
class NearbyAttractionCard:
    """A nearby attraction card from the details page."""

    content_id: str
    name: str
    rating: float
    num_reviews: int
    distance: str
    category: str
    photo_url: str


@dataclass
class NearbyRestaurantCard:
    """A nearby restaurant card from the attraction details page."""

    content_id: str
    name: str
    rating: float
    num_reviews: int
    distance: str
    cuisine: str
    photo_url: str


@dataclass
class AttractionDetail:
    """
    Full details of a single attraction from TripAdvisor.
    Pure domain model — no framework awareness.
    """

    content_id: str
    name: str
    rating: float
    num_reviews: int
    ranking: str
    category: str
    description: str
    address: str
    latitude: float
    longitude: float
    phone: str
    website: str
    hours_status: str
    today_schedule: list[str] = field(default_factory=list)
    about_items: list[str] = field(default_factory=list)
    photos: list[AttractionPhoto] = field(default_factory=list)
    reviews: list[AttractionReview] = field(default_factory=list)
    nearby_attractions: list[NearbyAttractionCard] = field(default_factory=list)
    nearby_restaurants: list[NearbyRestaurantCard] = field(default_factory=list)
