"""
Playlist domain entities.

A Playlist is a curated, shareable collection of attractions and restaurants
for a specific city.  Users can build playlists, tag them with a vibe and
budget tier, and others can discover, fork, and import them into trip schedules.

PlaylistItems are organized by day-number and time-slot so the playlist maps
directly onto a trip schedule on import.

Reviews allow the community to rate and comment on playlists.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ── Enums ────────────────────────────────────────────────────────────────────────


class PlaylistVibe(str, Enum):
    CHILL = "chill"
    ADVENTURE = "adventure"
    CULTURAL = "cultural"
    FOODIE = "foodie"
    NIGHTLIFE = "nightlife"
    ROMANTIC = "romantic"
    FAMILY = "family"
    INSTAGRAM = "instagram"
    HIDDEN_GEMS = "hidden_gems"
    LUXURY = "luxury"
    BACKPACKER = "backpacker"
    WELLNESS = "wellness"


class BudgetTier(str, Enum):
    ULTRA_BUDGET = "ultra_budget"
    BUDGET = "budget"
    MID_RANGE = "mid_range"
    PREMIUM = "premium"
    LUXURY = "luxury"


class PlaylistItemType(str, Enum):
    ATTRACTION = "attraction"
    RESTAURANT = "restaurant"
    CUSTOM = "custom"


class PlaylistTimeSlot(str, Enum):
    MORNING = "morning"
    MIDDAY = "midday"
    EVENING = "evening"
    NIGHT = "night"


# ── Value Objects ────────────────────────────────────────────────────────────────


@dataclass
class PlaylistItem:
    """
    One entry in a playlist — an attraction, restaurant, or custom spot.
    Organized by day_number + time_slot for direct schedule import.
    """
    item_type: PlaylistItemType
    name: str
    day_number: int                     # 1-based day within the playlist (Day 1, Day 2…)
    time_slot: PlaylistTimeSlot         # When to visit
    order: int = 0                      # Sort order within the same day+slot

    # Optional TripAdvisor-sourced fields (empty for custom items)
    location_id: str = ""               # TripAdvisor location ID
    category: str = ""                  # e.g. "Museums", "Italian"
    photo_url: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    address: str = ""
    rating: float = 0.0
    num_reviews: int = 0
    price_indicator: str = ""           # e.g. "$$", "Free", "Tickets from $20"

    # Creator-authored content
    note: str = ""                      # Personal tip / warning from the creator
    suggested_duration_minutes: int = 60


@dataclass
class PlaylistReview:
    """A community review on a playlist."""
    id: str = ""
    playlist_id: str = ""
    user_id: str = ""
    user_first_name: str = ""           # Snapshot for display
    user_last_name: str = ""
    rating: int = 5                     # 1–5 stars
    comment: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


# ── Aggregate Root ───────────────────────────────────────────────────────────────


@dataclass
class Playlist:
    """
    Pure domain model — no MongoDB or FastAPI awareness.
    A shareable, city-scoped collection of attractions + restaurants + custom spots.
    """
    creator_id: str
    city: str
    country: str
    title: str
    description: str = ""
    cover_photo_url: str = ""

    vibe: list[PlaylistVibe] = field(default_factory=lambda: [PlaylistVibe.CHILL])
    budget_tier: BudgetTier = BudgetTier.MID_RANGE

    items: list[PlaylistItem] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    total_days: int = 1                         # How many days this playlist covers

    is_public: bool = True
    like_count: int = 0
    import_count: int = 0
    liked_by: list[str] = field(default_factory=list)   # user_ids who liked

    # Aggregated review stats
    review_count: int = 0
    average_rating: float = 0.0

    id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # ── Domain logic ─────────────────────────────────────────────────────────

    def is_owner(self, user_id: str) -> bool:
        """Return True if user_id is the playlist creator."""
        return self.creator_id == user_id

    def toggle_like(self, user_id: str) -> bool:
        """Toggle like for a user. Returns True if now liked, False if unliked."""
        if user_id in self.liked_by:
            self.liked_by.remove(user_id)
            self.like_count = max(0, self.like_count - 1)
            return False
        self.liked_by.append(user_id)
        self.like_count += 1
        return True

    def update_review_stats(self, avg_rating: float, count: int) -> None:
        """Update cached review statistics."""
        self.average_rating = round(avg_rating, 2)
        self.review_count = count

