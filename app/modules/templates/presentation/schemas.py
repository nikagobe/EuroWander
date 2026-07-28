"""Pydantic schemas for Trip Templates — optimized for Flutter frontend."""

from pydantic import BaseModel, ConfigDict


# ─── Hotel pick schemas ──────────────────────────────────────────────

class HotelPickInput(BaseModel):
    booking_hotel_id: int
    name: str
    city: str
    neighborhood: str = ""
    stars: int = 0
    photo_url: str = ""
    author_review: str = ""
    priority: int = 1
    price_paid: float | None = None
    currency: str = "EUR"


class HotelRecommendationsInput(BaseModel):
    city: str
    country: str
    primary_picks: list[HotelPickInput] = []
    fallback_neighborhood: str = ""
    fallback_star_min: int = 1
    fallback_star_max: int = 5
    fallback_budget_per_night_min: float | None = None
    fallback_budget_per_night_max: float | None = None


# ─── Leg input ────────────────────────────────────────────────────────

class TemplateLegInput(BaseModel):
    order: int
    city: str
    country: str
    days: int
    hotel_recommendations: HotelRecommendationsInput | None = None
    playlist_id: str = ""
    restaurant_ids: list[str] = []
    author_notes: str = ""


# ─── Request schemas ──────────────────────────────────────────────────

class CreateTemplateRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "author_id": "user_123",
            "title": "7 Days in Spain",
            "description": "Budget backpacking route through Barcelona and Madrid",
            "legs": [
                {"order": 1, "city": "Barcelona", "country": "Spain", "days": 4},
                {"order": 2, "city": "Madrid", "country": "Spain", "days": 3},
            ],
            "tags": ["spain", "budget"],
        }
    })
    author_id: str
    title: str
    description: str = ""
    legs: list[TemplateLegInput]
    tags: list[str] = []
    cover_photo_url: str = ""
    estimated_budget_min: float | None = None
    estimated_budget_max: float | None = None
    currency: str = "EUR"


class UpdateTemplateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    legs: list[TemplateLegInput] | None = None
    tags: list[str] | None = None
    cover_photo_url: str | None = None
    estimated_budget_min: float | None = None
    estimated_budget_max: float | None = None
    currency: str | None = None


# ─── Response schemas ─────────────────────────────────────────────────

class HotelPickResponse(BaseModel):
    booking_hotel_id: int
    name: str
    city: str
    neighborhood: str
    stars: int
    photo_url: str
    author_review: str
    priority: int
    price_paid: float | None
    currency: str


class HotelRecommendationsResponse(BaseModel):
    city: str
    country: str
    primary_picks: list[HotelPickResponse]
    fallback_neighborhood: str
    fallback_star_min: int
    fallback_star_max: int
    fallback_budget_per_night_min: float | None
    fallback_budget_per_night_max: float | None


class TemplateLegResponse(BaseModel):
    order: int
    city: str
    country: str
    days: int
    hotel_recommendations: HotelRecommendationsResponse | None
    playlist_id: str
    restaurant_ids: list[str]
    author_notes: str


class TemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    author_id: str
    title: str
    description: str
    legs: list[TemplateLegResponse]
    tags: list[str]
    cover_photo_url: str
    estimated_budget_min: float | None
    estimated_budget_max: float | None
    currency: str
    total_days: int
    status: str
    fork_count: int
    like_count: int
    created_at: str
    updated_at: str


class TemplateListItem(BaseModel):
    """Lightweight response for list views."""
    id: str
    author_id: str
    title: str
    description: str
    tags: list[str]
    cover_photo_url: str
    total_days: int
    estimated_budget_min: float | None
    estimated_budget_max: float | None
    currency: str
    fork_count: int
    like_count: int
    status: str
    leg_cities: list[str]
