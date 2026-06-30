from datetime import date as DateType

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.buses.domain.entities import BusOffer, BusSegment


# ── Request ──────────────────────────────────────────────────────────────────

class BusSearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin_freebase_id": "/m/0156q",
                "destination_freebase_id": "/m/04jpl",
                "date": "2026-06-12",
                "adults": 1,
                "currency": "EUR",
                "limit": 20,
            }
        }
    )

    origin_freebase_id: str         # e.g. "/m/0156q"  (Berlin)
    destination_freebase_id: str    # e.g. "/m/04jpl"  (Munich)
    date: str                       # YYYY-MM-DD
    adults: int = Field(default=1, ge=1, le=9, description="Number of adult passengers (1-9)")
    currency: str = "EUR"
    limit: int = 20

    @field_validator("origin_freebase_id", "destination_freebase_id")
    @classmethod
    def strip_ws(cls, v: str) -> str:
        return v.strip()

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        # Accept YYYY-MM-DD; will be converted to DD.MM.YYYY for Flixbus
        DateType.fromisoformat(v)
        return v


# ── Response ──────────────────────────────────────────────────────────────────

class BusSegmentResponse(BaseModel):
    dep_name: str
    arr_name: str
    dep_time: str
    arr_time: str
    product_type: str
    product: str

    @classmethod
    def from_entity(cls, seg: BusSegment) -> "BusSegmentResponse":
        return cls(
            dep_name=seg.dep_name,
            arr_name=seg.arr_name,
            dep_time=seg.dep_time,
            arr_time=seg.arr_time,
            product_type=seg.product_type,
            product=seg.product,
        )


class BusOfferResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "dep_name": "Berlin central bus station",
                "arr_name": "Munich central bus station",
                "dep_time": "2026-06-12T08:00:00.000",
                "arr_time": "2026-06-12T15:40:00.000",
                "duration": "07:40",
                "duration_minutes": 460,
                "changeovers": 0,
                "price": 26.99,
                "price_per_person": 26.99,
                "total_price": 53.98,
                "currency": "EUR",
                "adults": 2,
                "deeplink": "https://shop.flixbus.com/...",
                "additional_info": "",
                "source": "flixbus",
                "segments": [],
            }
        }
    )

    dep_name: str
    arr_name: str
    dep_time: str
    arr_time: str
    duration: str
    duration_minutes: int
    changeovers: int
    price: float                # Per-person price
    price_per_person: float     # Same as price (FlixBus quotes per person)
    total_price: float          # price × adults
    currency: str
    adults: int                 # Number of passengers
    deeplink: str
    additional_info: str
    source: str
    segments: list[BusSegmentResponse]

    @classmethod
    def from_entity(cls, offer: BusOffer) -> "BusOfferResponse":
        return cls(
            dep_name=offer.dep_name,
            arr_name=offer.arr_name,
            dep_time=offer.dep_time,
            arr_time=offer.arr_time,
            duration=offer.duration,
            duration_minutes=offer.duration_minutes,
            changeovers=offer.changeovers,
            price=offer.price,
            price_per_person=offer.price_per_person,
            total_price=offer.total_price,
            currency=offer.currency,
            adults=offer.adults,
            deeplink=offer.deeplink,
            additional_info=offer.additional_info,
            source=offer.source,
            segments=[BusSegmentResponse.from_entity(s) for s in offer.segments],
        )

