from pydantic import BaseModel, ConfigDict

from app.modules.attractions.domain.entities import (
    AttractionDetails,
    AttractionLocation,
    AttractionPhoto,
    AttractionReview,
)


# ── Responses ─────────────────────────────────────────────────────────────────


class AttractionLocationResponse(BaseModel):
    """Search result for an attraction or restaurant."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location_id": "197572",
                "name": "Eiffel Tower",
                "address": "Champ de Mars, 5 Avenue Anatole France, 75007 Paris",
                "latitude": 48.8584,
                "longitude": 2.2945,
                "category": "attractions",
            }
        }
    )

    location_id: str
    name: str
    address: str
    latitude: float
    longitude: float
    category: str

    @classmethod
    def from_entity(cls, entity: AttractionLocation) -> "AttractionLocationResponse":
        return cls(
            location_id=entity.location_id,
            name=entity.name,
            address=entity.address,
            latitude=entity.latitude,
            longitude=entity.longitude,
            category=entity.category,
        )


class AttractionPhotoResponse(BaseModel):
    photo_id: str
    url_small: str
    url_medium: str
    url_large: str
    caption: str
    user: str

    @classmethod
    def from_entity(cls, entity: AttractionPhoto) -> "AttractionPhotoResponse":
        return cls(
            photo_id=entity.photo_id,
            url_small=entity.url_small,
            url_medium=entity.url_medium,
            url_large=entity.url_large,
            caption=entity.caption,
            user=entity.user,
        )


class AttractionReviewResponse(BaseModel):
    review_id: str
    rating: int
    title: str
    text: str
    published_date: str
    user_name: str

    @classmethod
    def from_entity(cls, entity: AttractionReview) -> "AttractionReviewResponse":
        return cls(
            review_id=entity.review_id,
            rating=entity.rating,
            title=entity.title,
            text=entity.text,
            published_date=entity.published_date,
            user_name=entity.user_name,
        )


class AttractionDetailsResponse(BaseModel):
    """Full details for a single attraction or restaurant."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location_id": "197572",
                "name": "Eiffel Tower",
                "description": "Built for the 1889 World's Fair...",
                "latitude": 48.8584,
                "longitude": 2.2945,
                "address": "Champ de Mars, 5 Avenue Anatole France, 75007 Paris",
                "phone": "+33 892 70 12 39",
                "website": "https://www.toureiffel.paris",
                "email": "",
                "category": "attractions",
                "subcategories": ["Observation Decks & Towers", "Points of Interest & Landmarks"],
                "rating": 4.5,
                "num_reviews": 142000,
                "ranking_string": "#5 of 3,199 things to do in Paris",
                "price_level": "$$",
                "hours": ["Monday: 09:30 - 23:45", "Tuesday: 09:30 - 23:45"],
                "cuisine": [],
                "photos": [],
                "reviews": [],
            }
        }
    )

    location_id: str
    name: str
    description: str
    latitude: float
    longitude: float
    address: str
    phone: str
    website: str
    email: str
    category: str
    subcategories: list[str]
    rating: float
    num_reviews: int
    ranking_string: str
    price_level: str
    hours: list[str]
    cuisine: list[str]
    photos: list[AttractionPhotoResponse]
    reviews: list[AttractionReviewResponse]

    @classmethod
    def from_entity(cls, entity: AttractionDetails) -> "AttractionDetailsResponse":
        return cls(
            location_id=entity.location_id,
            name=entity.name,
            description=entity.description,
            latitude=entity.latitude,
            longitude=entity.longitude,
            address=entity.address,
            phone=entity.phone,
            website=entity.website,
            email=entity.email,
            category=entity.category,
            subcategories=entity.subcategories,
            rating=entity.rating,
            num_reviews=entity.num_reviews,
            ranking_string=entity.ranking_string,
            price_level=entity.price_level,
            hours=entity.hours,
            cuisine=entity.cuisine,
            photos=[AttractionPhotoResponse.from_entity(p) for p in entity.photos],
            reviews=[AttractionReviewResponse.from_entity(r) for r in entity.reviews],
        )

