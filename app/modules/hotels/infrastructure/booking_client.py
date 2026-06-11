"""
Booking.com client via RapidAPI (booking-com15.p.rapidapi.com).
Handles destination autocomplete, hotel search, and hotel details.
"""

import json
import logging
from datetime import date as DateType

import httpx

logger = logging.getLogger(__name__)

from app.modules.hotels.domain.entities import (
    HotelDestination,
    HotelDetails,
    HotelOffer,
    HotelRoom,
    HotelRoomHighlight,
)
from app.modules.hotels.domain.interfaces import (
    HotelDestinationProvider,
    HotelDetailsProvider,
    HotelSearchProvider,
)

_DESTINATION_URL = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchDestination"
_SEARCH_URL = "https://booking-com15.p.rapidapi.com/api/v1/hotels/searchHotels"
_DETAILS_URL = "https://booking-com15.p.rapidapi.com/api/v1/hotels/getHotelDetails"


class BookingComClient(HotelDestinationProvider, HotelSearchProvider, HotelDetailsProvider):
    """Calls the RapidAPI Booking.com wrapper for destination, search, and details."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-rapidapi-host": "booking-com15.p.rapidapi.com",
            "x-rapidapi-key": self._api_key,
        }

    async def search_destinations(self, query: str) -> list[HotelDestination]:
        """
        Query the Booking.com autocomplete endpoint and map results
        to domain HotelDestination entities.
        """
        params = {"query": query}

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                _DESTINATION_URL,
                params=params,
                headers=self._headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            payload: dict = response.json()

        return _parse_destinations(payload)

    async def search_hotels(
        self,
        dest_id: str,
        search_type: str,
        arrival_date: str,
        departure_date: str,
        adults: int,
        room_qty: int,
        page_number: int,
        currency_code: str,
        sort_by: str,
        price_min: int | None,
        price_max: int | None,
    ) -> list[HotelOffer]:
        """
        Search hotels via the Booking.com searchHotels endpoint.
        """
        params: dict[str, str | int] = {
            "dest_id": dest_id,
            "search_type": search_type,
            "arrival_date": arrival_date,
            "departure_date": departure_date,
            "adults": str(adults),
            "room_qty": str(room_qty),
            "page_number": str(page_number),
            "currency_code": currency_code,
            "sort_by": sort_by,
            "units": "metric",
            "temperature_unit": "c",
            "languagecode": "en-us",
        }
        if price_min is not None:
            params["price_min"] = str(price_min)
        if price_max is not None:
            params["price_max"] = str(price_max)

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                _SEARCH_URL,
                params=params,
                headers=self._headers(),
                timeout=20.0,
            )
            response.raise_for_status()
            payload: dict = response.json()

        logger.info(
            "RapidAPI hotel search response:\n%s",
            json.dumps(payload, indent=2, ensure_ascii=False),
        )

        return _parse_hotels(payload)

    async def get_hotel_details(
        self,
        hotel_id: int,
        arrival_date: str,
        departure_date: str,
        adults: int,
        room_qty: int,
        currency_code: str,
    ) -> HotelDetails | None:
        """
        Fetch detailed hotel information via getHotelDetails endpoint.
        """
        params: dict[str, str] = {
            "hotel_id": str(hotel_id),
            "arrival_date": arrival_date,
            "departure_date": departure_date,
            "adults": str(adults),
            "room_qty": str(room_qty),
            "units": "metric",
            "temperature_unit": "c",
            "languagecode": "en-us",
            "currency_code": currency_code,
        }

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                _DETAILS_URL,
                params=params,
                headers=self._headers(),
                timeout=20.0,
            )
            response.raise_for_status()
            payload: dict = response.json()

        return _parse_hotel_details(payload)


# ── Parsers ────────────────────────────────────────────────────────────────────


def _parse_destinations(payload: dict) -> list[HotelDestination]:
    """
    Parse the raw RapidAPI response into a list of HotelDestination entities.
    Only extracts dest_id, city_name, and label.
    """
    if not payload.get("status"):
        return []

    data: list[dict] = payload.get("data", [])
    results: list[HotelDestination] = []

    for item in data:
        dest_id = item.get("dest_id", "")
        city_name = item.get("city_name", "")
        label = item.get("label", "")

        if dest_id and label:
            results.append(
                HotelDestination(
                    dest_id=str(dest_id),
                    city_name=city_name,
                    label=label,
                )
            )

    return results


def _parse_hotels(payload: dict) -> list[HotelOffer]:
    """
    Parse the raw searchHotels response into a list of HotelOffer entities.
    Extracts only the essential fields for the Flutter frontend.
    """
    if not payload.get("status"):
        return []

    data: dict = payload.get("data", {})
    hotels_raw: list[dict] = data.get("hotels", [])
    results: list[HotelOffer] = []

    for item in hotels_raw:
        prop: dict = item.get("property", {})
        if not prop:
            continue

        # Extract price from priceBreakdown.grossPrice
        price_breakdown: dict = prop.get("priceBreakdown", {})
        gross_price: dict = price_breakdown.get("grossPrice", {})
        excluded_price: dict = price_breakdown.get("excludedPrice", {})

        total: float = round(gross_price.get("value", 0.0), 2)
        excluded: float = round(excluded_price.get("value", 0.0), 2)

        # Compute per-night price from checkin/checkout dates
        checkin_date_str: str = prop.get("checkinDate", "")
        checkout_date_str: str = prop.get("checkoutDate", "")
        nights: int = 1
        if checkin_date_str and checkout_date_str:
            try:
                checkin_dt = DateType.fromisoformat(checkin_date_str)
                checkout_dt = DateType.fromisoformat(checkout_date_str)
                diff = (checkout_dt - checkin_dt).days
                if diff > 0:
                    nights = diff
            except ValueError:
                pass
        per_night: float = round(total / nights, 2)

        # Extract photo URL (first in list)
        photo_urls: list[str] = prop.get("photoUrls", [])
        photo_url = photo_urls[0] if photo_urls else ""

        # Extract checkin/checkout times
        checkin_info: dict = prop.get("checkin", {})
        checkout_info: dict = prop.get("checkout", {})

        results.append(
            HotelOffer(
                hotel_id=prop.get("id", 0),
                name=prop.get("name", ""),
                latitude=prop.get("latitude", 0.0),
                longitude=prop.get("longitude", 0.0),
                photo_url=photo_url,
                stars=prop.get("propertyClass", 0),
                review_score=prop.get("reviewScore", 0.0),
                review_score_word=prop.get("reviewScoreWord", ""),
                review_count=prop.get("reviewCount", 0),
                price_total=total,
                price_per_night=per_night,
                price_excluded=excluded,
                currency=gross_price.get("currency", ""),
                checkin_from=checkin_info.get("fromTime", ""),
                checkout_until=checkout_info.get("untilTime", ""),
                country_code=prop.get("countryCode", ""),
            )
        )

    return results



def _parse_hotel_details(payload: dict) -> HotelDetails | None:
    """
    Parse the raw getHotelDetails response into a HotelDetails entity.
    Extracts essential fields: info, photos, facilities, rooms, pricing.
    """
    if not payload.get("status"):
        return None

    data: dict = payload.get("data", {})
    if not data:
        return None

    # ── Price extraction ──
    price_breakdown: dict = data.get("composite_price_breakdown", {})
    gross_per_night: dict = price_breakdown.get("gross_amount_per_night", {})
    all_inclusive: dict = price_breakdown.get("all_inclusive_amount", {})
    excluded_amount: dict = price_breakdown.get("excluded_amount", {})

    # ── Checkin / Checkout times ──
    checkin_info: dict = data.get("checkin", {})
    checkout_info: dict = data.get("checkout", {})

    # ── Facilities ──
    facilities_block: dict = data.get("facilities_block", {})
    facilities_raw: list[dict] = facilities_block.get("facilities", [])
    facilities: list[str] = [f.get("name", "") for f in facilities_raw if f.get("name")]

    # ── Photos from rooms ──
    rooms_raw: dict = data.get("rooms", {})
    photos: list[str] = []
    rooms: list[HotelRoom] = []

    for room_id, room_data in rooms_raw.items():
        # Collect high-res photos
        room_photos: list[str] = []
        for photo in room_data.get("photos", []):
            url = photo.get("url_max1280") or photo.get("url_original", "")
            if url:
                room_photos.append(url)
                photos.append(url)

        # Room highlights
        highlights: list[HotelRoomHighlight] = [
            HotelRoomHighlight(
                name=h.get("translated_name", ""),
                icon=h.get("icon", ""),
            )
            for h in room_data.get("highlights", [])
            if h.get("translated_name")
        ]

        # Bed configurations
        bed_configs: list[str] = []
        for config in room_data.get("bed_configurations", []):
            for bed_type in config.get("bed_types", []):
                name_with_count = bed_type.get("name_with_count", "")
                if name_with_count:
                    bed_configs.append(name_with_count)

        # Room surface
        room_surface: float = 0.0
        for block in data.get("block", []):
            if str(block.get("room_id", "")) == room_id:
                room_surface = float(block.get("room_surface_in_m2", 0) or 0)
                break

        rooms.append(
            HotelRoom(
                room_id=room_id,
                description=room_data.get("description", ""),
                photos=room_photos,
                highlights=highlights,
                bed_configurations=bed_configs,
                room_surface_m2=room_surface,
            )
        )

    # ── Breakfast ──
    breakfast_included: bool = bool(data.get("hotel_include_breakfast", 0))

    # ── Distance to city center ──
    distance_to_cc: float = 0.0
    raw_distance = data.get("distance_to_cc", 0)
    try:
        distance_to_cc = round(float(raw_distance), 2)
    except (ValueError, TypeError):
        pass

    return HotelDetails(
        hotel_id=data.get("hotel_id", 0),
        name=data.get("hotel_name", ""),
        url=data.get("url", ""),
        description=data.get("hotel_description", ""),
        latitude=data.get("latitude", 0.0),
        longitude=data.get("longitude", 0.0),
        address=data.get("address", ""),
        city=data.get("city", ""),
        district=data.get("district", ""),
        country=data.get("country_trans", ""),
        country_code=data.get("countrycode", ""),
        zip_code=data.get("zip", ""),
        accommodation_type=data.get("accommodation_type_name", ""),
        stars=int(data.get("class", 0) or 0),
        review_score=float(data.get("review_score", 0) or 0),
        review_score_word=data.get("review_score_word", ""),
        review_count=data.get("review_nr", 0),
        currency=gross_per_night.get("currency", data.get("currency_code", "")),
        price_per_night=round(gross_per_night.get("value", 0.0), 2),
        price_total=round(all_inclusive.get("value", 0.0), 2),
        price_excluded=round(excluded_amount.get("value", 0.0), 2),
        available_rooms=data.get("available_rooms", 0),
        breakfast_included=breakfast_included,
        checkin_from=checkin_info.get("from", ""),
        checkin_until=checkin_info.get("until", ""),
        checkout_from=checkout_info.get("from", ""),
        checkout_until=checkout_info.get("until", ""),
        distance_to_center_km=distance_to_cc,
        facilities=facilities,
        photos=photos,
        rooms=rooms,
    )
