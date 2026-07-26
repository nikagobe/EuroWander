"""
Profile domain entities.

UserProfile stores personalization data in a separate collection from auth.
TravelStats, FrequentCollaborator, and Badge are value objects computed
from trip data — they are never persisted directly.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Badge(str, Enum):
    """Milestone badges a traveller can earn."""
    FIRST_TRIP = "first_trip"
    COUNTRIES_5 = "countries_5"
    COUNTRIES_10 = "countries_10"
    COUNTRIES_20 = "countries_20"
    FREQUENT_FLYER = "frequent_flyer"      # 10+ flights booked
    BUS_EXPLORER = "bus_explorer"          # 5+ bus journeys
    PLANNER_PRO = "planner_pro"            # 10+ trips created
    COLLABORATOR = "collaborator"          # 5+ shared trips


class TravelStyle(str, Enum):
    BUDGET = "budget"
    BACKPACKER = "backpacker"
    FOODIE = "foodie"
    ADVENTURE = "adventure"
    LUXURY = "luxury"
    CULTURAL = "cultural"
    SOLO = "solo"
    FAMILY = "family"


@dataclass
class UserProfile:
    """Personalization data stored in its own MongoDB collection.
    Linked to the User document via user_id."""
    user_id: str
    bio: str = ""
    home_city: str = ""
    base_airport: str = ""                          # IATA code
    profile_photo_url: str = ""
    cover_photo_url: str = ""
    preferred_languages: list[str] = field(default_factory=list)
    travel_style_tags: list[str] = field(default_factory=list)
    id: str = ""
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TravelStats:
    """Read-only value object computed from trip data."""
    trips_completed: int = 0
    cities_visited: list[str] = field(default_factory=list)
    total_distance_km: float = 0.0
    favorite_destination: str = ""


@dataclass
class FrequentCollaborator:
    """Value object representing a user frequently travelled with."""
    user_id: str
    first_name: str
    last_name: str
    profile_photo_url: str
    shared_trip_count: int

