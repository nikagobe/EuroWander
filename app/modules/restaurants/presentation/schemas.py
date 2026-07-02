from pydantic import BaseModel, ConfigDict

from app.modules.restaurants.domain.entities import (
    NearbyRestaurant,
    Restaurant,
    RestaurantDetail,
    RestaurantPhoto,
    RestaurantReview,
)


class RestaurantResponse(BaseModel):
    """A single restaurant in search results."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location_id": "2281697",
                "name": "Aloha Isle",
                "cuisine": "$ • Quick Bites • American • Fast Food",
                "neighborhood": "Lake Buena Vista",
                "rating": 4.6,
                "num_reviews": 1414,
                "photo_url": "https://dynamic-media-cdn.tripadvisor.com/media/photo-o/...",
                "badge": "TRAVELLER_CHOICE",
                "badge_year": "2025",
                "price_level": "$",
                "is_sponsored": False,
            }
        }
    )

    location_id: str
    name: str
    cuisine: str
    neighborhood: str
    rating: float
    num_reviews: int
    photo_url: str
    badge: str
    badge_year: str
    price_level: str
    is_sponsored: bool

    @classmethod
    def from_entity(cls, entity: Restaurant) -> "RestaurantResponse":
        return cls(
            location_id=entity.location_id,
            name=entity.name,
            cuisine=entity.cuisine,
            neighborhood=entity.neighborhood,
            rating=entity.rating,
            num_reviews=entity.num_reviews,
            photo_url=entity.photo_url,
            badge=entity.badge,
            badge_year=entity.badge_year,
            price_level=entity.price_level,
            is_sponsored=entity.is_sponsored,
        )


class PaginationMeta(BaseModel):
    """Pagination metadata for Flutter list views."""

    current_page: int
    total_pages: int
    total_results: int
    page_size: int
    update_token: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_page": 1,
                "total_pages": 9,
                "total_results": 260,
                "page_size": 30,
                "update_token": "eyJ2ZXIiOiJ2MiIs...",
            }
        }
    )


class PaginatedRestaurantResponse(BaseModel):
    """Paginated list of restaurants for Flutter infinite scroll."""

    data: list[RestaurantResponse]
    pagination: PaginationMeta

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [
                    {
                        "location_id": "2281697",
                        "name": "Aloha Isle",
                        "cuisine": "$ • Quick Bites • American",
                        "neighborhood": "",
                        "rating": 4.6,
                        "num_reviews": 1414,
                        "photo_url": "...",
                        "badge": "TRAVELLER_CHOICE",
                        "badge_year": "2025",
                        "price_level": "$",
                        "is_sponsored": False,
                    }
                ],
                "pagination": {
                    "current_page": 1,
                    "total_pages": 9,
                    "total_results": 260,
                    "page_size": 30,
                    "update_token": "eyJ2ZXIiOiJ2MiIs...",
                },
            }
        }
    )


# ── Restaurant Details Schemas ─────────────────────────────────────────────────


class RestaurantPhotoResponse(BaseModel):
    """A single restaurant photo."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://dynamic-media-cdn.tripadvisor.com/media/photo-o/1b/b3/4f/e1/restaurant.jpg?w=800&h=600&s=1",
                "caption": "Rita's Italian Ice and Frozen Custards",
                "width": 2500,
                "height": 1667,
            }
        }
    )

    url: str
    caption: str
    width: int
    height: int

    @classmethod
    def from_entity(cls, entity: RestaurantPhoto) -> "RestaurantPhotoResponse":
        return cls(
            url=entity.url,
            caption=entity.caption,
            width=entity.width,
            height=entity.height,
        )


class RestaurantReviewResponse(BaseModel):
    """A user review for a restaurant."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating": 5.0,
                "title": "Great!",
                "text": "We went yesterday and the staff were so friendly...",
                "author": "Vasoulla S",
                "published_date": "Aug 2023",
                "trip_type": "Aug 2023 • Family",
            }
        }
    )

    rating: float
    title: str
    text: str
    author: str
    published_date: str
    trip_type: str

    @classmethod
    def from_entity(cls, entity: RestaurantReview) -> "RestaurantReviewResponse":
        return cls(
            rating=entity.rating,
            title=entity.title,
            text=entity.text,
            author=entity.author,
            published_date=entity.published_date,
            trip_type=entity.trip_type,
        )


class NearbyRestaurantResponse(BaseModel):
    """A nearby restaurant card."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content_id": "338f4740-6f42-466f-851d-40e4b187f917",
                "name": "The Cheesecake Factory",
                "rating": 3.5,
                "num_reviews": 180,
                "distance": "0.3 mi",
                "cuisine": "$$ - $$$ • American • Seafood • Fast Food",
                "photo_url": "https://dynamic-media-cdn.tripadvisor.com/media/photo-o/...",
            }
        }
    )

    content_id: str
    name: str
    rating: float
    num_reviews: int
    distance: str
    cuisine: str
    photo_url: str

    @classmethod
    def from_entity(cls, entity: NearbyRestaurant) -> "NearbyRestaurantResponse":
        return cls(
            content_id=entity.content_id,
            name=entity.name,
            rating=entity.rating,
            num_reviews=entity.num_reviews,
            distance=entity.distance,
            cuisine=entity.cuisine,
            photo_url=entity.photo_url,
        )


class RestaurantDetailResponse(BaseModel):
    """Full restaurant detail response optimized for Flutter."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content_id": "27717696",
                "name": "Rita's Italian Ice and Frozen Custard",
                "rating": 4.5,
                "num_reviews": 8,
                "ranking": "#942 of 2,069 Restaurants in Orlando",
                "price_level": "$",
                "description": "Italian Ice and Frozen Custard serving up smiles...",
                "address": "11567 Regency Village Dr, Orlando, FL 32821-7825",
                "latitude": 28.39383,
                "longitude": -81.48415,
                "phone": "+1 407-239-4494",
                "website": "https://www.ritasice.com/",
                "hours_status": "Closed now",
                "today_schedule": ["Opens 12:00 PM - 9:00 PM"],
                "serving": ["Dinner"],
                "features": ["Delivery", "Takeout", "Seating"],
                "cuisines": [],
                "photos": [],
                "reviews": [],
                "nearby_restaurants": [],
            }
        }
    )

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
    today_schedule: list[str]
    serving: list[str]
    features: list[str]
    cuisines: list[str]
    photos: list[RestaurantPhotoResponse]
    reviews: list[RestaurantReviewResponse]
    nearby_restaurants: list[NearbyRestaurantResponse]

    @classmethod
    def from_entity(cls, entity: RestaurantDetail) -> "RestaurantDetailResponse":
        return cls(
            content_id=entity.content_id,
            name=entity.name,
            rating=entity.rating,
            num_reviews=entity.num_reviews,
            ranking=entity.ranking,
            price_level=entity.price_level,
            description=entity.description,
            address=entity.address,
            latitude=entity.latitude,
            longitude=entity.longitude,
            phone=entity.phone,
            website=entity.website,
            hours_status=entity.hours_status,
            today_schedule=entity.today_schedule,
            serving=entity.serving,
            features=entity.features,
            cuisines=entity.cuisines,
            photos=[RestaurantPhotoResponse.from_entity(p) for p in entity.photos],
            reviews=[RestaurantReviewResponse.from_entity(r) for r in entity.reviews],
            nearby_restaurants=[NearbyRestaurantResponse.from_entity(n) for n in entity.nearby_restaurants],
        )
