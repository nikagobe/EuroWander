"""Pydantic schemas for Trip Templates — optimized for Flutter frontend."""

from pydantic import BaseModel, ConfigDict, Field


# ─── Nested input schemas ─────────────────────────────────────────────

class FlightRecommendationInput(BaseModel):
    origin_iata: str
    destination_iata: str
    origin_city: str
    destination_city: str
    preferred_airlines: list[str] = []
    preferred_flight_numbers: list[str] = []
    preferred_departure_window: str = "any"
    typical_price_min: float | None = None
    typical_price_max: float | None = None
    typical_duration_minutes: int | None = None
    tip: str = ""


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


class TransportRecommendationInput(BaseModel):
    from_city: str
    to_city: str
    mode: str
    preferred_providers: list[str] = []
    typical_duration_minutes: int | None = None
    typical_price: float | None = None
    currency: str = "EUR"
    tip: str = ""


class TemplateLegInput(BaseModel):
    order: int
    city: str
    country: str
    days: int
    flight_recommendation: FlightRecommendationInput | None = None
    transport_recommendation: TransportRecommendationInput | None = None
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
            "legs": [],
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


class ForkGuideRequest(BaseModel):
    start_date: str = Field(..., description="YYYY-MM-DD start date for the trip")


# ─── Response schemas ─────────────────────────────────────────────────

class FlightRecommendationResponse(BaseModel):
    origin_iata: str
    destination_iata: str
    origin_city: str
    destination_city: str
    preferred_airlines: list[str]
    preferred_flight_numbers: list[str]
    preferred_departure_window: str
    typical_price_min: float | None
    typical_price_max: float | None
    typical_duration_minutes: int | None
    tip: str


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


class TransportRecommendationResponse(BaseModel):
    from_city: str
    to_city: str
    mode: str
    preferred_providers: list[str]
    typical_duration_minutes: int | None
    typical_price: float | None
    currency: str
    tip: str


class TemplateLegResponse(BaseModel):
    order: int
    city: str
    country: str
    days: int
    flight_recommendation: FlightRecommendationResponse | None
    transport_recommendation: TransportRecommendationResponse | None
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
    leg_cities: list[str]  # quick preview of cities in route

