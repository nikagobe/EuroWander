"""
TripAdvisor Terra API client for restaurant details.
Uses the same Terra API as attractions — works for any location type.
"""

import asyncio
import logging
from datetime import datetime

import httpx

from app.modules.restaurants.domain.entities import (
    RestaurantDetail,
    RestaurantPhoto,
    RestaurantReview,
)
from app.modules.restaurants.domain.interfaces import RestaurantDetailProvider

logger = logging.getLogger(__name__)

_BASE_URL = "https://terra.tripadvisor.com/api"


class TerraRestaurantDetailClient(RestaurantDetailProvider):
    """
    Fetches restaurant details from the official TripAdvisor Terra API.
    Calls /locations/{id} + /locations/{id}/photos in parallel.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Accept": "application/json",
        }

    async def get_restaurant_details(
        self,
        content_id: str,
        currency: str,
    ) -> RestaurantDetail:
        """Fetch restaurant details + photos in parallel from Terra API."""
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            details_coro = client.get(
                f"{_BASE_URL}/locations/{content_id}",
                headers=self._headers(),
                params={"locale": "en-US"},
            )
            photos_coro = client.get(
                f"{_BASE_URL}/locations/{content_id}/photos",
                headers=self._headers(),
                params={"locale": "en-US", "size": 10},
            )

            details_resp, photos_resp = await asyncio.gather(
                details_coro, photos_coro, return_exceptions=True
            )

        # Parse details
        location: dict = {}
        if isinstance(details_resp, httpx.Response) and details_resp.status_code == 200:
            location = details_resp.json()
            logger.info(
                "Terra restaurant details [200]: id=%s, %.2fs",
                content_id,
                details_resp.elapsed.total_seconds(),
            )
        elif isinstance(details_resp, httpx.Response):
            logger.error("Terra restaurant details [%s]: %s", details_resp.status_code, details_resp.text[:200])
            details_resp.raise_for_status()
        else:
            raise details_resp  # type: ignore[misc]

        # Parse photos
        photos: list[RestaurantPhoto] = []
        if isinstance(photos_resp, httpx.Response) and photos_resp.status_code == 200:
            photos = _parse_photos(photos_resp.json())
        elif isinstance(photos_resp, httpx.Response):
            logger.warning("Terra restaurant photos [%s]: %s", photos_resp.status_code, photos_resp.text[:200])

        return _map_to_entity(location, content_id, photos)

    async def get_reviews(
        self,
        location_id: str,
        language: str = "en",
        page: int = 1,
        size: int = 5,
    ) -> list[RestaurantReview]:
        """Fetch reviews for a restaurant from Terra API."""
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.get(
                f"{_BASE_URL}/locations/{location_id}/reviews",
                headers=self._headers(),
                params={"language": language, "page": page, "size": size},
            )

        if resp.status_code != 200:
            logger.error("Terra restaurant reviews [%s]: %s", resp.status_code, resp.text[:200])
            return []

        logger.info("Terra restaurant reviews [200]: id=%s, %.2fs", location_id, resp.elapsed.total_seconds())
        return _parse_reviews(resp.json())

    async def get_nearby(
        self,
        location_id: str,
        category: str = "RESTAURANT",
        size: int = 10,
    ) -> list[dict]:
        """Fetch nearby restaurants from Terra API."""
        params: dict[str, str | int] = {
            "location_id": location_id,
            "radius": 5,
            "unit": "KM",
            "size": size,
            "locale": "en-US",
            "include_photo": "true",
            "category": category,
        }

        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.get(
                f"{_BASE_URL}/locations/nearby",
                headers=self._headers(),
                params=params,
            )

        if resp.status_code != 200:
            logger.error("Terra restaurant nearby [%s]: %s", resp.status_code, resp.text[:200])
            return []

        logger.info("Terra restaurant nearby [200]: id=%s, %.2fs", location_id, resp.elapsed.total_seconds())
        payload: dict = resp.json()
        return payload.get("data", [])


# ── Mappers ─────────────────────────────────────────────────────────────────────


def _get_primary_name(location: dict) -> str:
    """Extract primary name from location names array."""
    names: list[dict] = location.get("names", [])
    for n in names:
        if n.get("primary"):
            return n.get("value", "")
    return names[0].get("value", "") if names else ""


def _map_to_entity(
    location: dict, content_id: str, photos: list[RestaurantPhoto]
) -> RestaurantDetail:
    """Map Terra API location response to RestaurantDetail entity."""
    name: str = _get_primary_name(location)

    # Rating & reviews
    traveler_ratings: dict = location.get("traveler_ratings", {})
    overall: dict = traveler_ratings.get("overall", {})
    rating: float = float(overall.get("rating", 0) or 0)
    num_reviews: int = int(overall.get("count", 0) or 0)

    # Ranking
    rankings: list[dict] = location.get("rankings", [])
    ranking: str = rankings[0].get("display_text", "") if rankings else ""

    # Price level
    price_level: str = location.get("price_level", "") or ""

    # Description
    descriptions: list[dict] = location.get("descriptions", [])
    description: str = descriptions[0].get("value", "") if descriptions else ""

    # Address
    addresses: list[dict] = location.get("addresses", [])
    address: str = addresses[0].get("formatted", "") if addresses else ""

    # Coordinates
    coords: dict = location.get("coordinates", {})
    latitude: float = float(coords.get("latitude", 0) or 0)
    longitude: float = float(coords.get("longitude", 0) or 0)

    # Phone
    phone_numbers: list[dict] = location.get("phone_numbers", [])
    phone: str = phone_numbers[0].get("value", "") if phone_numbers else ""

    # Website
    urls: dict = location.get("urls", {})
    website: str = urls.get("official", "") or ""

    # Hours
    opening_hours: dict = location.get("opening_hours", {}) or {}
    formatted_hours: list[str] = opening_hours.get("formatted", []) or []

    # Status
    status: dict = location.get("status", {})
    status_value: str = status.get("value", "")
    hours_status: str = _format_status(status_value)

    # Categories → cuisines
    categories: list[dict] = location.get("categories", []) or []
    cuisines: list[str] = [c.get("display_name", "") for c in categories if c.get("display_name")]

    # Attributes → features
    attributes: list[dict] = location.get("attributes", []) or []
    features: list[str] = [a.get("name", "") for a in attributes if a.get("name")]

    return RestaurantDetail(
        content_id=content_id,
        name=name,
        rating=rating,
        num_reviews=num_reviews,
        ranking=ranking,
        price_level=price_level,
        description=description,
        address=address,
        latitude=latitude,
        longitude=longitude,
        phone=phone,
        website=website,
        hours_status=hours_status,
        today_schedule=formatted_hours,
        serving=[],  # Not available in Terra; keep empty
        features=features,
        cuisines=cuisines,
        photos=photos,
        reviews=[],  # Reviews are a separate endpoint now
        nearby_restaurants=[],  # Nearby is a separate endpoint now
    )


def _format_status(status_value: str) -> str:
    """Convert Terra status enum to user-friendly string."""
    mapping: dict[str, str] = {
        "OPEN": "Open",
        "CLOSED": "Permanently Closed",
        "TEMPORARILY_CLOSED": "Temporarily Closed",
    }
    return mapping.get(status_value, status_value)


def _parse_photos(payload: dict) -> list[RestaurantPhoto]:
    """Parse Terra photos response into RestaurantPhoto entities."""
    photos: list[RestaurantPhoto] = []
    data: list[dict] = payload.get("data", [])

    for item in data:
        photo_info: dict = item.get("photo", {})
        url: str = photo_info.get("original_size_url", "")
        if not url:
            continue
        caption: str = item.get("caption", "") or ""
        width: int = photo_info.get("original_width", 0) or 0
        height: int = photo_info.get("original_height", 0) or 0
        photos.append(RestaurantPhoto(url=url, caption=caption, width=width, height=height))

    return photos


def _parse_reviews(payload: dict) -> list[RestaurantReview]:
    """Parse Terra reviews response into RestaurantReview entities."""
    reviews: list[RestaurantReview] = []
    data: list[dict] = payload.get("data", [])

    for item in data:
        rating: float = float(item.get("rating", 0) or 0)

        title_list: list[dict] = item.get("title", [])
        title: str = _get_primary_translation(title_list)

        text_list: list[dict] = item.get("text", [])
        text: str = _get_primary_translation(text_list)

        user: dict = item.get("user", {}) or {}
        author: str = user.get("username", "")

        publish_ts: str = item.get("publish_ts", "")
        published_date: str = _format_date(publish_ts)

        trip_type: str = (item.get("trip_type", "") or "").replace("_", " ").title()

        reviews.append(
            RestaurantReview(
                rating=rating,
                title=title,
                text=text,
                author=author,
                published_date=published_date,
                trip_type=trip_type,
            )
        )

    return reviews


def _get_primary_translation(translations: list[dict]) -> str:
    """Get the primary translation value."""
    for t in translations:
        if t.get("primary"):
            return t.get("value", "")
    return translations[0].get("value", "") if translations else ""


def _format_date(iso_ts: str) -> str:
    """Format ISO timestamp to readable date like 'Jun 30, 2026'."""
    if not iso_ts:
        return ""
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return iso_ts

