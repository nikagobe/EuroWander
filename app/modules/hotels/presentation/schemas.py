from datetime import date as DateType

from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.hotels.domain.entities import (
    HotelDestination,
    HotelDetails,
    HotelOffer,
    HotelRoom,
    HotelRoomHighlight,
)


# ── Requests ──────────────────────────────────────────────────────────────────

class HotelSearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dest_id": "-2092174",
                "search_type": "CITY",
                "arrival_date": "2026-06-23",
                "departure_date": "2026-06-26",
                "adults": 1,
                "room_qty": 1,
                "page_number": 1,
                "currency_code": "EUR",
                "sort_by": "price",
                "price_min": None,
                "price_max": None,
            }
        }
    )

    dest_id: str                        # Booking.com dest_id from /destinations
    search_type: str = "CITY"           # CITY, DISTRICT, etc.
    arrival_date: str                   # YYYY-MM-DD
    departure_date: str                 # YYYY-MM-DD
    adults: int = 1
    room_qty: int = 1                   # Number of rooms needed
    page_number: int = 1
    currency_code: str = "EUR"
    sort_by: str = "price"              # price, review_score, popularity, etc.
    price_min: int | None = None
    price_max: int | None = None

    @field_validator("arrival_date", "departure_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        DateType.fromisoformat(v)
        return v


# ── Responses ─────────────────────────────────────────────────────────────────

class HotelDestinationResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dest_id": "-2602512",
                "city_name": "Manchester",
                "label": "Manchester, Greater Manchester, United Kingdom",
                "search_type": "city",
                "hotel_id": None,
            }
        }
    )

    dest_id: str
    city_name: str
    label: str
    search_type: str        # "city", "district", "hotel", "landmark"
    hotel_id: int | None    # only set when search_type == "hotel"

    @classmethod
    def from_entity(cls, entity: HotelDestination) -> "HotelDestinationResponse":
        return cls(
            dest_id=entity.dest_id,
            city_name=entity.city_name,
            label=entity.label,
            search_type=entity.search_type,
            hotel_id=entity.hotel_id,
        )


class HotelOfferResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hotel_id": 9400894,
                "name": "Martinhal Lisbon Oriente",
                "latitude": 38.761582,
                "longitude": -9.098131,
                "photo_url": "https://cf.bstatic.com/xdata/images/hotel/square500/466945356.jpg",
                "stars": 5,
                "review_score": 9.6,
                "review_score_word": "Exceptional",
                "review_count": 1358,
                "price_total": 1340.54,
                "price_per_night": 268.11,
                "price_excluded": 79.23,
                "currency": "EUR",
                "checkin_from": "15:00",
                "checkout_until": "11:00",
                "country_code": "pt",
            }
        }
    )

    hotel_id: int
    name: str
    latitude: float
    longitude: float
    photo_url: str
    stars: int
    review_score: float
    review_score_word: str
    review_count: int
    price_total: float
    price_per_night: float
    price_excluded: float
    currency: str
    checkin_from: str
    checkout_until: str
    country_code: str

    @classmethod
    def from_entity(cls, entity: HotelOffer) -> "HotelOfferResponse":
        return cls(
            hotel_id=entity.hotel_id,
            name=entity.name,
            latitude=entity.latitude,
            longitude=entity.longitude,
            photo_url=entity.photo_url,
            stars=entity.stars,
            review_score=entity.review_score,
            review_score_word=entity.review_score_word,
            review_count=entity.review_count,
            price_total=entity.price_total,
            price_per_night=entity.price_per_night,
            price_excluded=entity.price_excluded,
            currency=entity.currency,
            checkin_from=entity.checkin_from,
            checkout_until=entity.checkout_until,
            country_code=entity.country_code,
        )


# ── Hotel Details Response ────────────────────────────────────────────────────


class RoomHighlightResponse(BaseModel):
    name: str
    icon: str

    @classmethod
    def from_entity(cls, entity: HotelRoomHighlight) -> "RoomHighlightResponse":
        return cls(name=entity.name, icon=entity.icon)


class HotelRoomResponse(BaseModel):
    room_id: str
    description: str
    photos: list[str]
    highlights: list[RoomHighlightResponse]
    bed_configurations: list[str]
    room_surface_m2: float

    @classmethod
    def from_entity(cls, entity: HotelRoom) -> "HotelRoomResponse":
        return cls(
            room_id=entity.room_id,
            description=entity.description,
            photos=entity.photos,
            highlights=[RoomHighlightResponse.from_entity(h) for h in entity.highlights],
            bed_configurations=entity.bed_configurations,
            room_surface_m2=entity.room_surface_m2,
        )


class HotelDetailsResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "hotel_id": 9400894,
                "name": "Martinhal Lisbon Oriente",
                "url": "https://www.booking.com/hotel/pt/martinhal-lisbon-oriente.html",
                "description": "Located in Parque das Nações, this 5-star aparthotel offers...",
                "latitude": 38.761582,
                "longitude": -9.098131,
                "address": "Rua do Oriente 100",
                "city": "Lisbon",
                "district": "Parque das Nações",
                "country": "Portugal",
                "country_code": "pt",
                "zip_code": "1990-221",
                "accommodation_type": "Hotels",
                "stars": 5,
                "review_score": 9.6,
                "review_score_word": "Exceptional",
                "review_count": 1358,
                "currency": "EUR",
                "price_per_night": 268.11,
                "price_total": 1340.54,
                "price_excluded": 79.23,
                "available_rooms": 3,
                "breakfast_included": True,
                "checkin_from": "15:00",
                "checkin_until": "00:00",
                "checkout_from": "00:00",
                "checkout_until": "11:00",
                "distance_to_center_km": 6.4,
                "facilities": ["Free WiFi", "Swimming pool", "Restaurant"],
                "photos": ["https://cf.bstatic.com/xdata/images/hotel/max1280x900/466945356.jpg"],
                "rooms": [],
            }
        }
    )

    hotel_id: int
    name: str
    url: str
    description: str
    latitude: float
    longitude: float
    address: str
    city: str
    district: str
    country: str
    country_code: str
    zip_code: str
    accommodation_type: str
    stars: int
    review_score: float
    review_score_word: str
    review_count: int
    currency: str
    price_per_night: float
    price_total: float
    price_excluded: float
    available_rooms: int
    breakfast_included: bool
    checkin_from: str
    checkin_until: str
    checkout_from: str
    checkout_until: str
    distance_to_center_km: float
    facilities: list[str]
    photos: list[str]
    rooms: list[HotelRoomResponse]

    @classmethod
    def from_entity(cls, entity: HotelDetails) -> "HotelDetailsResponse":
        return cls(
            hotel_id=entity.hotel_id,
            name=entity.name,
            url=entity.url,
            description=entity.description,
            latitude=entity.latitude,
            longitude=entity.longitude,
            address=entity.address,
            city=entity.city,
            district=entity.district,
            country=entity.country,
            country_code=entity.country_code,
            zip_code=entity.zip_code,
            accommodation_type=entity.accommodation_type,
            stars=entity.stars,
            review_score=entity.review_score,
            review_score_word=entity.review_score_word,
            review_count=entity.review_count,
            currency=entity.currency,
            price_per_night=entity.price_per_night,
            price_total=entity.price_total,
            price_excluded=entity.price_excluded,
            available_rooms=entity.available_rooms,
            breakfast_included=entity.breakfast_included,
            checkin_from=entity.checkin_from,
            checkin_until=entity.checkin_until,
            checkout_from=entity.checkout_from,
            checkout_until=entity.checkout_until,
            distance_to_center_km=entity.distance_to_center_km,
            facilities=entity.facilities,
            photos=entity.photos,
            rooms=[HotelRoomResponse.from_entity(r) for r in entity.rooms],
        )


