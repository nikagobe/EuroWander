from dataclasses import dataclass, field


@dataclass
class Restaurant:
    """
    A single restaurant from TripAdvisor search results.
    Pure domain model — no MongoDB or FastAPI awareness.
    """

    location_id: str            # TripAdvisor location ID
    name: str                   # Restaurant name (without ranking prefix)
    cuisine: str                # e.g. "$$ - $$$ • Japanese • Bar • Vegetarian friendly"
    neighborhood: str           # e.g. "Lake Buena Vista" or ""
    rating: float               # Bubble rating 1.0–5.0
    num_reviews: int            # Total review count
    photo_url: str              # Photo URL (resized)
    badge: str                  # e.g. "TRAVELLER_CHOICE" or ""
    badge_year: str             # e.g. "2025" or ""
    price_level: str            # Extracted price tag: "$", "$$ - $$$", "$$$$", ""
    is_sponsored: bool          # Whether the listing is a sponsored ad


@dataclass
class PaginatedRestaurants:
    """A page of restaurant results with pagination metadata."""

    items: list[Restaurant]
    current_page: int
    total_pages: int
    total_results: int
    page_size: int
    update_token: str           # Token for fetching subsequent pages


@dataclass
class RestaurantPhoto:
    """A single photo for a restaurant."""

    url: str
    caption: str
    width: int
    height: int


@dataclass
class RestaurantReview:
    """A user review for a restaurant."""

    rating: float
    title: str
    text: str
    author: str
    published_date: str
    trip_type: str


@dataclass
class NearbyRestaurant:
    """A nearby restaurant card."""

    content_id: str
    name: str
    rating: float
    num_reviews: int
    distance: str
    cuisine: str
    photo_url: str


@dataclass
class RestaurantDetail:
    """
    Full details of a single restaurant from TripAdvisor.
    Pure domain model — no framework awareness.
    """

    content_id: str
    name: str
    rating: float
    num_reviews: int
    ranking: str
    price_level: str
    description: str
    address: str
    latitude: float
    longitude: float
    phone: str
    website: str
    hours_status: str
    today_schedule: list[str] = field(default_factory=list)
    serving: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    cuisines: list[str] = field(default_factory=list)
    photos: list[RestaurantPhoto] = field(default_factory=list)
    reviews: list[RestaurantReview] = field(default_factory=list)
    nearby_restaurants: list[NearbyRestaurant] = field(default_factory=list)

