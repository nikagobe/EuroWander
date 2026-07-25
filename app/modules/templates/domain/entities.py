"""
Trip Template domain entities.

A TripTemplate is a reusable travel blueprint: an ordered list of cities
to visit, with recommended hotels, attractions playlists, and restaurants.

Transportation (flights, buses) is NOT part of the template — every user
departs from a different city, so transport is chosen at fork time.

Templates are date-agnostic — concrete dates are chosen at fork time.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TemplateStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


@dataclass
class HotelPick:
    """A specific hotel the template author recommends."""
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


@dataclass
class HotelRecommendations:
    """Hotel guidance for one city/leg — primary picks + fallback params."""
    city: str
    country: str
    primary_picks: list[HotelPick] = field(default_factory=list)
    fallback_neighborhood: str = ""
    fallback_star_min: int = 1
    fallback_star_max: int = 5
    fallback_budget_per_night_min: float | None = None
    fallback_budget_per_night_max: float | None = None


@dataclass
class TemplateLeg:
    """One city/stop in the template itinerary."""
    order: int
    city: str
    country: str
    days: int
    hotel_recommendations: HotelRecommendations | None = None
    playlist_id: str = ""
    restaurant_ids: list[str] = field(default_factory=list)
    author_notes: str = ""


@dataclass
class TripTemplate:
    """Pure domain model for a reusable trip blueprint."""
    author_id: str
    title: str
    description: str
    legs: list[TemplateLeg]
    tags: list[str] = field(default_factory=list)
    cover_photo_url: str = ""
    estimated_budget_min: float | None = None
    estimated_budget_max: float | None = None
    currency: str = "EUR"
    total_days: int = 0
    status: TemplateStatus = TemplateStatus.DRAFT
    fork_count: int = 0
    like_count: int = 0
    liked_by: list[str] = field(default_factory=list)
    id: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def is_author(self, user_id: str) -> bool:
        return self.author_id == user_id

    def can_be_published(self) -> bool:
        return bool(self.title) and len(self.legs) > 0

    def is_published(self) -> bool:
        return self.status == TemplateStatus.PUBLISHED

