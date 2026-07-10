"""Pydantic schemas for the Playlist module — optimized for Flutter."""

from pydantic import BaseModel, ConfigDict, Field


# ── Playlist Item ────────────────────────────────────────────────────────────────


class PlaylistItemSchema(BaseModel):
    """A single item in a playlist (request and response)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "item_type": "attraction",
                "name": "Eiffel Tower",
                "day_number": 1,
                "time_slot": "morning",
                "order": 0,
                "location_id": "188757",
                "category": "Landmarks",
                "photo_url": "https://...",
                "latitude": 48.8584,
                "longitude": 2.2945,
                "address": "Champ de Mars, Paris",
                "rating": 4.6,
                "num_reviews": 120000,
                "price_indicator": "Tickets from €26",
                "note": "⚠️ Beware of scammers near the base!",
                "suggested_duration_minutes": 120,
            }
        }
    )

    item_type: str                              # attraction | restaurant | custom
    name: str
    day_number: int = 1
    time_slot: str = "morning"                  # morning | midday | evening | night
    order: int = 0
    location_id: str = ""
    category: str = ""
    photo_url: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    address: str = ""
    rating: float = 0.0
    num_reviews: int = 0
    price_indicator: str = ""
    note: str = ""
    suggested_duration_minutes: int = 60


# ── Create / Update ─────────────────────────────────────────────────────────────


class CreatePlaylistRequest(BaseModel):
    """Request body to create a new playlist."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "city": "Paris",
                "country": "France",
                "title": "Hidden Gems of Paris",
                "description": "Off-the-beaten-path spots for culture lovers",
                "vibe": "hidden_gems",
                "budget_tier": "budget",
                "tags": ["culture", "local", "walking"],
                "total_days": 2,
                "items": [],
            }
        }
    )

    city: str
    country: str
    title: str
    description: str = ""
    cover_photo_url: str = ""
    vibe: str = "chill"
    budget_tier: str = "mid_range"
    tags: list[str] = Field(default_factory=list)
    total_days: int = 1
    is_public: bool = True
    items: list[PlaylistItemSchema] = Field(default_factory=list)


class UpdatePlaylistRequest(BaseModel):
    """Partial update for a playlist."""

    title: str | None = None
    description: str | None = None
    cover_photo_url: str | None = None
    city: str | None = None
    country: str | None = None
    vibe: str | None = None
    budget_tier: str | None = None
    tags: list[str] | None = None
    total_days: int | None = None
    is_public: bool | None = None
    items: list[PlaylistItemSchema] | None = None


# ── Responses ────────────────────────────────────────────────────────────────────


class PlaylistResponse(BaseModel):
    """Full playlist response for Flutter."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "abc-123",
                "creator_id": "user_1",
                "city": "Paris",
                "country": "France",
                "title": "Hidden Gems of Paris",
                "vibe": "hidden_gems",
                "budget_tier": "budget",
                "like_count": 42,
                "import_count": 15,
                "review_count": 8,
                "average_rating": 4.3,
                "total_days": 2,
            }
        }
    )

    id: str
    creator_id: str
    city: str
    country: str
    title: str
    description: str
    cover_photo_url: str
    vibe: str
    budget_tier: str
    items: list[PlaylistItemSchema]
    tags: list[str]
    total_days: int
    is_public: bool
    like_count: int
    import_count: int
    review_count: int
    average_rating: float
    created_at: str
    updated_at: str


class PlaylistSummaryResponse(BaseModel):
    """Lightweight playlist card for search results / lists."""

    id: str
    creator_id: str
    city: str
    country: str
    title: str
    description: str
    cover_photo_url: str
    vibe: str
    budget_tier: str
    total_days: int
    item_count: int
    like_count: int
    import_count: int
    review_count: int
    average_rating: float
    tags: list[str]


# ── Reviews ──────────────────────────────────────────────────────────────────────


class CreateReviewRequest(BaseModel):
    """Request body to add a review."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating": 5,
                "comment": "Amazing playlist! Used it for my Rome trip.",
            }
        }
    )

    rating: int = Field(ge=1, le=5)
    comment: str = ""


class ReviewResponse(BaseModel):
    """A single review response."""

    id: str
    playlist_id: str
    user_id: str
    user_first_name: str
    user_last_name: str
    rating: int
    comment: str
    created_at: str


# ── Import ───────────────────────────────────────────────────────────────────────


class ImportPlaylistRequest(BaseModel):
    """Request body to import a playlist into a trip schedule."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "start_date": "2026-07-27",
            }
        }
    )

    start_date: str   # YYYY-MM-DD — first day to map playlist Day 1 onto


# ── Like toggle ──────────────────────────────────────────────────────────────────


class LikeResponse(BaseModel):
    liked: bool
    like_count: int

