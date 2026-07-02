from pydantic import BaseModel, ConfigDict

from app.modules.attractions.domain.entities import (
    Attraction,
    AttractionDestination,
    AttractionDetail,
)


class AttractionDestinationResponse(BaseModel):
    """Autocomplete result for a city destination (for attraction browsing)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "geo_id": 187147,
                "name": "Paris",
                "secondary_text": "Ile-de-France, France",
                "image_url": "",
            }
        }
    )

    geo_id: int
    name: str
    secondary_text: str
    image_url: str

    @classmethod
    def from_entity(cls, entity: AttractionDestination) -> "AttractionDestinationResponse":
        return cls(
            geo_id=entity.geo_id,
            name=entity.name,
            secondary_text=entity.secondary_text,
            image_url=entity.image_url,
        )


class AttractionResponse(BaseModel):
    """A single attraction in search results."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "location_id": "143395",
                "name": "Magic Kingdom Park",
                "category": "Amusement & Theme Parks",
                "neighborhood": "Lake Buena Vista",
                "rating": 4.4,
                "num_reviews": 69877,
                "photo_url": "https://dynamic-media-cdn.tripadvisor.com/media/photo-o/...",
                "latitude": 28.418764,
                "longitude": -81.58122,
                "badge": "BEST_OF_BEST",
                "ticket_price": "Tickets from $91 USD",
                "is_open_now": False,
            }
        }
    )

    location_id: str
    name: str
    category: str
    neighborhood: str
    rating: float
    num_reviews: int
    photo_url: str
    latitude: float
    longitude: float
    badge: str
    ticket_price: str
    is_open_now: bool

    @classmethod
    def from_entity(cls, entity: Attraction) -> "AttractionResponse":
        return cls(
            location_id=entity.location_id,
            name=entity.name,
            category=entity.category,
            neighborhood=entity.neighborhood,
            rating=entity.rating,
            num_reviews=entity.num_reviews,
            photo_url=entity.photo_url,
            latitude=entity.latitude,
            longitude=entity.longitude,
            badge=entity.badge,
            ticket_price=entity.ticket_price,
            is_open_now=entity.is_open_now,
        )


class PaginationMeta(BaseModel):
    """Pagination metadata for Flutter list views."""

    current_page: int
    total_pages: int
    total_results: int
    page_size: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"current_page": 1, "total_pages": 8, "total_results": 223, "page_size": 30}
        }
    )


class PaginatedAttractionResponse(BaseModel):
    """Paginated list of attractions for Flutter infinite scroll."""

    data: list[AttractionResponse]
    pagination: PaginationMeta

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": [{"location_id": "143395", "name": "Magic Kingdom Park", "category": "Amusement & Theme Parks", "neighborhood": "", "rating": 4.4, "num_reviews": 69877, "photo_url": "...", "latitude": 28.42, "longitude": -81.58, "badge": "BEST_OF_BEST", "ticket_price": "Tickets from $91 USD", "is_open_now": False}],
                "pagination": {"current_page": 1, "total_pages": 8, "total_results": 223, "page_size": 30},
            }
        }
    )


# ── Attraction Detail Schemas ──────────────────────────────────────────────────


class AttractionPhotoResponse(BaseModel):
    """A single attraction photo."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://dynamic-media-cdn.tripadvisor.com/media/photo-o/.../photo.jpg?w=800&h=600&s=1",
                "caption": "Beautiful horses!",
                "width": 2048,
                "height": 1536,
            }
        }
    )

    url: str
    caption: str
    width: int
    height: int


class AttractionReviewResponse(BaseModel):
    """A user review for an attraction."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "rating": 5.0,
                "title": "Disney horses - free to visit",
                "text": "If you are staying in a Disney resort take some time...",
                "author": "miss_bell",
                "published_date": "Dec 8, 2025",
                "trip_type": "Couples",
            }
        }
    )

    rating: float
    title: str
    text: str
    author: str
    published_date: str
    trip_type: str


class NearbyAttractionCardResponse(BaseModel):
    """A nearby attraction from the details page."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content_id": "143395",
                "name": "Magic Kingdom Park",
                "rating": 4.4,
                "num_reviews": 69877,
                "distance": "3.7 km",
                "category": "Amusement & Theme Parks",
                "photo_url": "https://dynamic-media-cdn.tripadvisor.com/...",
            }
        }
    )

    content_id: str
    name: str
    rating: float
    num_reviews: int
    distance: str
    category: str
    photo_url: str


class NearbyRestaurantCardResponse(BaseModel):
    """A nearby restaurant from the attraction details page."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content_id": "7227399",
                "name": "Capa Bar",
                "rating": 4.3,
                "num_reviews": 507,
                "distance": "1.1 km",
                "cuisine": "$$$$ • Steakhouse • Spanish • Vegetarian friendly",
                "photo_url": "https://dynamic-media-cdn.tripadvisor.com/...",
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


class AttractionDetailResponse(BaseModel):
    """Full detail view of an attraction — optimized for Flutter detail screen."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content_id": "3436969",
                "name": "Tri-Circle-D Ranch",
                "rating": 4.4,
                "num_reviews": 84,
                "ranking": "#108 of 467 things to do in Orlando",
                "category": "Equestrian Trails",
                "description": "",
                "address": "4510 Fort Wilderness Trl Lake Buena Vista, Orlando, FL 32830-8415",
                "latitude": 28.39582,
                "longitude": -81.55327,
                "phone": "+1 407-939-7529",
                "website": "http://disneyworld.disney.go.com/recreation/tri-circle-d-ranch/",
                "hours_status": "Open Now",
                "today_schedule": ["8:00 AM - 3:30 PM"],
                "about_items": ["Meets animal welfare guidelines"],
                "photos": [],
                "reviews": [],
                "nearby_attractions": [],
                "nearby_restaurants": [],
            }
        }
    )

    content_id: str
    name: str
    rating: float
    num_reviews: int
    ranking: str
    category: str
    description: str
    address: str
    latitude: float
    longitude: float
    phone: str
    website: str
    hours_status: str
    today_schedule: list[str]
    about_items: list[str]
    photos: list[AttractionPhotoResponse]
    reviews: list[AttractionReviewResponse]
    nearby_attractions: list[NearbyAttractionCardResponse]
    nearby_restaurants: list[NearbyRestaurantCardResponse]

    @classmethod
    def from_entity(cls, entity: AttractionDetail) -> "AttractionDetailResponse":
        return cls(
            content_id=entity.content_id,
            name=entity.name,
            rating=entity.rating,
            num_reviews=entity.num_reviews,
            ranking=entity.ranking,
            category=entity.category,
            description=entity.description,
            address=entity.address,
            latitude=entity.latitude,
            longitude=entity.longitude,
            phone=entity.phone,
            website=entity.website,
            hours_status=entity.hours_status,
            today_schedule=entity.today_schedule,
            about_items=entity.about_items,
            photos=[
                AttractionPhotoResponse(
                    url=p.url, caption=p.caption, width=p.width, height=p.height
                )
                for p in entity.photos
            ],
            reviews=[
                AttractionReviewResponse(
                    rating=r.rating,
                    title=r.title,
                    text=r.text,
                    author=r.author,
                    published_date=r.published_date,
                    trip_type=r.trip_type,
                )
                for r in entity.reviews
            ],
            nearby_attractions=[
                NearbyAttractionCardResponse(
                    content_id=a.content_id,
                    name=a.name,
                    rating=a.rating,
                    num_reviews=a.num_reviews,
                    distance=a.distance,
                    category=a.category,
                    photo_url=a.photo_url,
                )
                for a in entity.nearby_attractions
            ],
            nearby_restaurants=[
                NearbyRestaurantCardResponse(
                    content_id=r.content_id,
                    name=r.name,
                    rating=r.rating,
                    num_reviews=r.num_reviews,
                    distance=r.distance,
                    cuisine=r.cuisine,
                    photo_url=r.photo_url,
                )
                for r in entity.nearby_restaurants
            ],
        )
