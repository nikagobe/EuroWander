from dataclasses import dataclass, field


@dataclass
class AttractionLocation:
    """
    A search result from TripAdvisor location search.
    Pure domain model — no MongoDB or FastAPI awareness.
    Covers both attractions and restaurants.
    """

    location_id: str                    # TripAdvisor location ID
    name: str                           # Place name
    address: str                        # Full street address
    latitude: float
    longitude: float
    category: str                       # "attractions" or "restaurants"


@dataclass
class AttractionPhoto:
    """A single photo associated with a location."""

    photo_id: str
    url_small: str                      # Thumbnail
    url_medium: str                     # Medium resolution
    url_large: str                      # Full resolution
    caption: str = ""
    user: str = ""                      # Attribution (who uploaded)


@dataclass
class AttractionReview:
    """A single user review for a location."""

    review_id: str
    rating: int                         # 1–5 bubble rating
    title: str
    text: str
    published_date: str                 # ISO date string
    user_name: str = ""


@dataclass
class AttractionDetails:
    """
    Detailed information for a single attraction or restaurant.
    Pure domain model — no MongoDB or FastAPI awareness.
    """

    location_id: str
    name: str
    description: str
    latitude: float
    longitude: float
    address: str
    phone: str
    website: str
    email: str
    category: str                       # "attractions" or "restaurants"
    subcategories: list[str] = field(default_factory=list)   # e.g. ["Museums", "Art Museums"]
    rating: float = 0.0                 # Average rating (1.0–5.0)
    num_reviews: int = 0
    ranking_string: str = ""            # e.g. "#5 of 200 things to do in Paris"
    price_level: str = ""               # e.g. "$", "$$", "$$$"
    hours: list[str] = field(default_factory=list)           # Operating hours per day
    cuisine: list[str] = field(default_factory=list)         # Restaurants only
    photos: list[AttractionPhoto] = field(default_factory=list)
    reviews: list[AttractionReview] = field(default_factory=list)

