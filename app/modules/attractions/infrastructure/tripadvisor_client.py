"""
TripAdvisor Terra Partner API client.
Handles nearby location search and location details.

API docs: https://docs.terra.tripadvisor.com
Base URL: https://terra.tripadvisor.com/api
Auth: X-API-Key header
"""

import logging
import math

import httpx

from app.modules.attractions.domain.entities import (
    AttractionDetails,
    AttractionLocation,
    AttractionPhoto,
    AttractionReview,
)
from app.modules.attractions.domain.interfaces import (
    AttractionDetailsProvider,
    AttractionSearchProvider,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://terra.tripadvisor.com/api"

# Map internal category names to Terra API enum values
_CATEGORY_MAP: dict[str, str] = {
    "attractions": "ATTRACTION",
    "restaurants": "RESTAURANT",
    "hotels": "HOTEL",
}

# Map short language codes to TripAdvisor supported locales
_LOCALE_MAP: dict[str, str] = {
    "en": "en-US",
    "fr": "fr-FR",
    "de": "de-DE",
    "es": "es-ES",
    "it": "it-IT",
    "pt": "pt-BR",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "ar": "ar",
    "da": "da-DK",
    "el": "el-GR",
    "fi": "fi",
    "he": "he-IL",
    "hu": "hu",
    "id": "id-ID",
    "nl": "nl-NL",
    "no": "no-NO",
    "pl": "pl-PL",
    "ru": "ru-RU",
    "sv": "sv-SE",
    "th": "th-TH",
    "tr": "tr-TR",
    "vi": "vi-VN",
    "zh": "zh-CN",
}


def _resolve_locale(language: str) -> str:
    """Convert short language code to TripAdvisor-supported locale."""
    # If already a full locale (e.g. 'en-US'), return as-is
    if "-" in language or "_" in language:
        return language
    return _LOCALE_MAP.get(language, "en-US")


class TripAdvisorClient(AttractionSearchProvider, AttractionDetailsProvider):
    """
    Calls the TripAdvisor Terra Partner API for location search and details.
    Implements both search and details provider interfaces.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Accept": "application/json",
        }

    # ── Search by keyword ──────────────────────────────────────────────────────

    async def search_locations(
        self,
        query: str,
        category: str,
        language: str,
    ) -> list[AttractionLocation]:
        """
        Search TripAdvisor locations by keyword and category.
        Uses the /locations/search endpoint.
        """
        params: dict[str, str] = {
            "query": query,
            "category": _CATEGORY_MAP.get(category, "ATTRACTION"),
            "locale": _resolve_locale(language),
        }

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{_BASE_URL}/locations/search",
                params=params,
                headers=self._headers(),
                timeout=15.0,
            )
            logger.info(
                "TripAdvisor /locations/search [%s]: %s",
                response.status_code,
                response.text[:500],
            )
            response.raise_for_status()
            payload: dict = response.json()

        return _parse_search_results(payload, category)

    # ── Nearby search ──────────────────────────────────────────────────────────

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        category: str,
        language: str,
    ) -> list[AttractionLocation]:
        """
        Search TripAdvisor locations near given coordinates.
        Uses bounding box (~15 km in each direction) to cover full city area,
        since radius is capped at 8 KM by the API.
        """
        # Calculate bounding box: ~15 km offset in each direction
        # 1 degree latitude ≈ 111 km, 1 degree longitude ≈ 111 * cos(lat) km
        offset_km = 15.0
        lat_offset = offset_km / 111.0
        lon_offset = offset_km / (111.0 * math.cos(math.radians(latitude)))

        params: dict[str, str | int | float] = {
            "sw_lat": latitude - lat_offset,
            "sw_lon": longitude - lon_offset,
            "ne_lat": latitude + lat_offset,
            "ne_lon": longitude + lon_offset,
            "category": _CATEGORY_MAP.get(category, "ATTRACTION"),
            "include_photo": "true",
            "sort": "rating,desc",
            "size": 20,
            "locale": _resolve_locale(language),
        }

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{_BASE_URL}/locations/nearby",
                params=params,
                headers=self._headers(),
                timeout=15.0,
            )
            logger.info(
                "TripAdvisor /locations/nearby [%s]: %s",
                response.status_code,
                response.text[:500],
            )
            if response.status_code == 403:
                raise PermissionError("nearby search not available on current API plan")
            response.raise_for_status()
            payload: dict = response.json()

        return _parse_nearby_results(payload, category)

    # ── Location details (with photos & reviews) ───────────────────────────────

    async def get_location_details(
        self,
        location_id: str,
        language: str,
        currency: str,
    ) -> AttractionDetails | None:
        """
        Fetch full details for a location.
        The nearby endpoint already returns rich data, so this fetches
        the single location endpoint for the complete representation.
        """
        params: dict[str, str] = {
            "locale": _resolve_locale(language),
            "include_photo": "true",
        }

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                f"{_BASE_URL}/locations/{location_id}",
                params=params,
                headers=self._headers(),
                timeout=15.0,
            )

        logger.info(
            "TripAdvisor /locations/%s [%s]: %s",
            location_id,
            response.status_code,
            response.text[:500],
        )

        if response.status_code != 200:
            logger.warning(
                "TripAdvisor location details request failed: %s %s",
                response.status_code,
                response.text[:200],
            )
            return None

        data: dict = response.json()
        return _parse_location_details(data)


# ── Parsers ────────────────────────────────────────────────────────────────────


def _parse_nearby_results(payload: dict, category: str) -> list[AttractionLocation]:
    """Parse the Terra Partner API /locations/nearby response."""
    data: list[dict] = payload.get("data", [])
    results: list[AttractionLocation] = []

    for item in data:
        location: dict = item.get("location", {})
        location_id = str(location.get("id", ""))
        names: list[dict] = location.get("names", [])
        name = _get_primary_name(names)
        addresses: list[dict] = location.get("addresses", [])
        address = addresses[0].get("formatted", "") if addresses else ""
        coords: dict = location.get("coordinates", {})
        latitude = float(coords.get("latitude", 0) or 0)
        longitude = float(coords.get("longitude", 0) or 0)

        if location_id and name:
            results.append(
                AttractionLocation(
                    location_id=location_id,
                    name=name,
                    address=address,
                    latitude=latitude,
                    longitude=longitude,
                    category=category,
                )
            )

    return results


def _parse_search_results(payload: dict, category: str) -> list[AttractionLocation]:
    """Parse the Terra Partner API /locations/search response."""
    data: list[dict] = payload.get("data", [])
    results: list[AttractionLocation] = []

    for item in data:
        # Search might return locations directly or wrapped
        location: dict = item.get("location", item)
        location_id = str(location.get("id", location.get("location_id", "")))
        names: list[dict] = location.get("names", [])
        name = _get_primary_name(names) or location.get("name", "")
        addresses: list[dict] = location.get("addresses", [])
        address = addresses[0].get("formatted", "") if addresses else ""
        # Fallback for older response format
        if not address:
            address_obj: dict = location.get("address_obj", {})
            address = address_obj.get("address_string", "")
        coords: dict = location.get("coordinates", {})
        latitude = float(coords.get("latitude", location.get("latitude", 0)) or 0)
        longitude = float(coords.get("longitude", location.get("longitude", 0)) or 0)

        if location_id and name:
            results.append(
                AttractionLocation(
                    location_id=location_id,
                    name=name,
                    address=address,
                    latitude=latitude,
                    longitude=longitude,
                    category=category,
                )
            )

    return results


def _parse_location_details(data: dict) -> AttractionDetails | None:
    """Parse the Terra Partner API single location response into domain entity."""
    if not data:
        return None

    location_id = str(data.get("id", ""))
    if not location_id:
        return None

    # Name
    names: list[dict] = data.get("names", [])
    name = _get_primary_name(names)

    # Description
    descriptions: list[dict] = data.get("descriptions", [])
    description = descriptions[0].get("value", "") if descriptions else ""

    # Coordinates
    coords: dict = data.get("coordinates", {})
    latitude = float(coords.get("latitude", 0) or 0)
    longitude = float(coords.get("longitude", 0) or 0)

    # Address
    addresses: list[dict] = data.get("addresses", [])
    address = addresses[0].get("formatted", "") if addresses else ""

    # Phone
    phone_numbers: list[dict] = data.get("phone_numbers", [])
    phone = phone_numbers[0].get("value", "") if phone_numbers else ""

    # URLs
    urls: dict = data.get("urls", {})
    website = urls.get("official", "")
    email = data.get("official_email", "")

    # Category
    categories: list[dict] = data.get("categories", [])
    category = "attractions"
    subcategories: list[str] = []
    for cat in categories:
        display_name = cat.get("display_name", "")
        top_level = cat.get("top_level_category", "")
        if top_level and "eat" in str(top_level).lower():
            category = "restaurants"
        if display_name:
            subcategories.append(display_name)

    # Rating
    traveler_ratings: dict = data.get("traveler_ratings", {})
    overall: dict = traveler_ratings.get("overall", {})
    rating = float(overall.get("rating", 0) or 0)
    num_reviews = int(overall.get("count", 0) or 0)

    # Ranking
    rankings: list[dict] = data.get("rankings", [])
    ranking_string = rankings[0].get("display_text", "") if rankings else ""

    # Price level
    price_level = data.get("price_level", "")

    # Hours
    opening_hours: dict = data.get("opening_hours", {})
    hours: list[str] = opening_hours.get("formatted", [])

    # Cuisine (from attributes or categories for restaurants)
    cuisine: list[str] = []
    attributes: list[dict] = data.get("attributes", [])
    for attr in attributes:
        attr_type = attr.get("type", "")
        if "cuisine" in attr_type.lower():
            cuisine.append(attr.get("name", ""))

    # Photos
    photos: list[AttractionPhoto] = []
    photo_info: dict = data.get("photos", {})
    # Single representative photo might be at top level
    # Full photos come from a separate endpoint if needed

    return AttractionDetails(
        location_id=location_id,
        name=name,
        description=description,
        latitude=latitude,
        longitude=longitude,
        address=address,
        phone=phone,
        website=website,
        email=email,
        category=category,
        subcategories=subcategories,
        rating=rating,
        num_reviews=num_reviews,
        ranking_string=ranking_string,
        price_level=price_level,
        hours=hours,
        cuisine=cuisine,
        photos=photos,
        reviews=[],  # Reviews require separate endpoint
    )


def _get_primary_name(names: list[dict]) -> str:
    """Extract the primary name from the names array, falling back to first entry."""
    for n in names:
        if n.get("primary"):
            return n.get("value", "")
    return names[0].get("value", "") if names else ""
