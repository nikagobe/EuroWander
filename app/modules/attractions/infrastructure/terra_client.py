"""
TripAdvisor Terra API client (terra.tripadvisor.com/api).
Handles location details + photos for attractions.
Fast, reliable, official API — replaces the RapidAPI scraper for details endpoints.
"""

import asyncio
import logging
from datetime import datetime

import httpx

from app.modules.attractions.domain.entities import (
    Attraction,
    AttractionDetail,
    AttractionPhoto,
    AttractionReview,
    PaginatedAttractions,
)
from app.modules.attractions.domain.interfaces import (
    AttractionDetailProvider,
    AttractionNameSearchProvider,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://terra.tripadvisor.com/api"


class TerraAttractionDetailClient(AttractionDetailProvider, AttractionNameSearchProvider):
    """
    Fetches attraction details from the official TripAdvisor Terra API.
    Calls /locations/{id} + /locations/{id}/photos in parallel for speed.
    Also supports free-text name search via /locations/search.
    """

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._api_key,
            "Accept": "application/json",
        }

    async def get_attraction_details(
        self,
        content_id: str,
        start_date: str,
        end_date: str,
        currency: str,
        adults: int,
    ) -> AttractionDetail:
        """
        Fetch attraction details + photos in parallel from Terra API.
        start_date, end_date, adults are unused by Terra but kept for interface compat.
        """
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
                "Terra details [200]: id=%s, name=%s, %.2fs",
                content_id,
                _get_primary_name(location),
                details_resp.elapsed.total_seconds(),
            )
        elif isinstance(details_resp, httpx.Response):
            logger.error("Terra details [%s]: %s", details_resp.status_code, details_resp.text[:200])
            details_resp.raise_for_status()
        else:
            raise details_resp  # type: ignore[misc]

        # Parse photos
        photos: list[AttractionPhoto] = []
        if isinstance(photos_resp, httpx.Response) and photos_resp.status_code == 200:
            photos = _parse_photos(photos_resp.json())
            logger.info("Terra photos [200]: id=%s, count=%d", content_id, len(photos))
        elif isinstance(photos_resp, httpx.Response):
            logger.warning("Terra photos [%s]: %s", photos_resp.status_code, photos_resp.text[:200])
        else:
            logger.warning("Terra photos failed: %s", photos_resp)

        return _map_to_entity(location, content_id, photos)

    async def get_reviews(
        self,
        location_id: str,
        language: str = "en",
        page: int = 1,
        size: int = 5,
    ) -> list[AttractionReview]:
        """Fetch reviews for a location from Terra API."""
        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.get(
                f"{_BASE_URL}/locations/{location_id}/reviews",
                headers=self._headers(),
                params={"language": language, "page": page, "size": size},
            )

        if resp.status_code != 200:
            logger.error("Terra reviews [%s]: %s", resp.status_code, resp.text[:200])
            return []

        logger.info("Terra reviews [200]: id=%s, %.2fs", location_id, resp.elapsed.total_seconds())
        return _parse_reviews(resp.json())

    async def get_nearby(
        self,
        location_id: str,
        category: str | None = None,
        size: int = 10,
    ) -> list[dict]:
        """Fetch nearby locations from Terra API. Returns raw dicts for flexibility."""
        params: dict[str, str | int] = {
            "location_id": location_id,
            "radius": 5,
            "unit": "KM",
            "size": size,
            "locale": "en-US",
            "include_photo": "true",
        }
        if category:
            params["category"] = category

        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.get(
                f"{_BASE_URL}/locations/nearby",
                headers=self._headers(),
                params=params,
            )

        if resp.status_code != 200:
            logger.error("Terra nearby [%s]: %s", resp.status_code, resp.text[:200])
            return []

        logger.info("Terra nearby [200]: id=%s, category=%s, %.2fs", location_id, category, resp.elapsed.total_seconds())
        payload: dict = resp.json()
        return payload.get("data", [])

    async def search_by_name(
        self,
        query: str,
        category: str | None = None,
        geo_name: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedAttractions:
        """
        Search locations by free-text name using Terra /locations/search.
        Does NOT require a geo_id — works globally or scoped by geo_name.
        """
        params: dict[str, str | int] = {
            "query": query,
            "search_type": "NAME",
            "page": page,
            "size": min(size, 20),
            "locale": "en-US",
        }
        if category:
            params["category"] = category.upper()
        if geo_name:
            params["geo_name"] = geo_name

        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.get(
                f"{_BASE_URL}/locations/search",
                headers=self._headers(),
                params=params,
            )

        logger.info(
            "Terra locations/search [%s]: query=%r, category=%s, %.2fs",
            resp.status_code,
            query,
            category,
            resp.elapsed.total_seconds(),
        )
        resp.raise_for_status()
        payload: dict = resp.json()
        return _parse_terra_search_results(payload)


# ── Mappers ─────────────────────────────────────────────────────────────────────


def _get_primary_name(location: dict) -> str:
    """Extract primary name from location names array."""
    names: list[dict] = location.get("names", [])
    for n in names:
        if n.get("primary"):
            return n.get("value", "")
    return names[0].get("value", "") if names else ""


def _map_to_entity(
    location: dict, content_id: str, photos: list[AttractionPhoto]
) -> AttractionDetail:
    """Map Terra API location response to the existing AttractionDetail entity."""
    # Name
    name: str = _get_primary_name(location)

    # Rating & reviews
    traveler_ratings: dict = location.get("traveler_ratings", {})
    overall: dict = traveler_ratings.get("overall", {})
    rating: float = float(overall.get("rating", 0) or 0)
    num_reviews: int = int(overall.get("count", 0) or 0)

    # Ranking
    rankings: list[dict] = location.get("rankings", [])
    ranking: str = rankings[0].get("display_text", "") if rankings else ""

    # Category
    categories: list[dict] = location.get("categories", [])
    category: str = categories[0].get("display_name", "") if categories else ""

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

    # About items (attributes)
    attributes: list[dict] = location.get("attributes", []) or []
    about_items: list[str] = [a.get("name", "") for a in attributes if a.get("name")]

    return AttractionDetail(
        content_id=content_id,
        name=name,
        rating=rating,
        num_reviews=num_reviews,
        ranking=ranking,
        category=category,
        description=description,
        address=address,
        latitude=latitude,
        longitude=longitude,
        phone=phone,
        website=website,
        hours_status=hours_status,
        today_schedule=formatted_hours,
        about_items=about_items,
        photos=photos,
        reviews=[],  # Reviews are a separate endpoint now
        nearby_attractions=[],  # Nearby is a separate endpoint now
        nearby_restaurants=[],
    )


def _format_status(status_value: str) -> str:
    """Convert Terra status enum to user-friendly string."""
    mapping: dict[str, str] = {
        "OPEN": "Open",
        "CLOSED": "Permanently Closed",
        "TEMPORARILY_CLOSED": "Temporarily Closed",
    }
    return mapping.get(status_value, status_value)


def _parse_photos(payload: dict) -> list[AttractionPhoto]:
    """Parse Terra photos response into domain entities."""
    photos: list[AttractionPhoto] = []
    data: list[dict] = payload.get("data", [])

    for item in data:
        photo_info: dict = item.get("photo", {})
        url: str = photo_info.get("original_size_url", "")
        if not url:
            continue
        caption: str = item.get("caption", "") or ""
        width: int = photo_info.get("original_width", 0) or 0
        height: int = photo_info.get("original_height", 0) or 0
        photos.append(AttractionPhoto(url=url, caption=caption, width=width, height=height))

    return photos


def _parse_reviews(payload: dict) -> list[AttractionReview]:
    """Parse Terra reviews response into domain entities."""
    reviews: list[AttractionReview] = []
    data: list[dict] = payload.get("data", [])

    for item in data:
        rating: float = float(item.get("rating", 0) or 0)

        # Title — get primary language value
        title_list: list[dict] = item.get("title", [])
        title: str = _get_primary_translation(title_list)

        # Text — get primary language value
        text_list: list[dict] = item.get("text", [])
        text: str = _get_primary_translation(text_list)

        # Author
        user: dict = item.get("user", {}) or {}
        author: str = user.get("username", "")

        # Published date
        publish_ts: str = item.get("publish_ts", "")
        published_date: str = _format_date(publish_ts)

        # Trip type
        trip_type: str = (item.get("trip_type", "") or "").replace("_", " ").title()

        reviews.append(
            AttractionReview(
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
    """Get the primary translation value from a list of TranslationWithPrimary objects."""
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


def _parse_terra_search_results(payload: dict) -> PaginatedAttractions:
    """Parse Terra /locations/search response into PaginatedAttractions."""
    data: list[dict] = payload.get("data", [])
    pagination: dict = payload.get("pagination", {})

    items: list[Attraction] = []
    for entry in data:
        location: dict = entry.get("location", {})
        if not location:
            continue

        loc_id: str = str(location.get("id", ""))
        if not loc_id:
            continue

        # Name
        names: list[dict] = location.get("names", [])
        name: str = ""
        for n in names:
            if n.get("primary"):
                name = n.get("value", "")
                break
        if not name and names:
            name = names[0].get("value", "")
        if not name:
            continue

        # Category
        categories: list[dict] = location.get("categories", [])
        category: str = categories[0].get("display_name", "") if categories else ""

        # Rating
        traveler_ratings: dict = location.get("traveler_ratings", {})
        overall: dict = traveler_ratings.get("overall", {})
        rating: float = float(overall.get("rating", 0) or 0)
        num_reviews: int = int(overall.get("count", 0) or 0)

        # Coordinates
        coords: dict = location.get("coordinates", {})
        latitude: float = float(coords.get("latitude", 0) or 0)
        longitude: float = float(coords.get("longitude", 0) or 0)

        # Address as neighborhood
        addresses: list[dict] = location.get("addresses", [])
        neighborhood: str = ""
        if addresses:
            city: str = addresses[0].get("city", "")
            country: str = addresses[0].get("country_name", "")
            neighborhood = f"{city}, {country}" if city and country else city or country

        # Photo — not available in search results
        photo_url: str = ""

        # Status
        status: dict = location.get("status", {})
        is_open: bool = status.get("value", "") == "OPEN"

        items.append(Attraction(
            location_id=loc_id,
            name=name,
            category=category,
            neighborhood=neighborhood,
            rating=rating,
            num_reviews=num_reviews,
            photo_url=photo_url,
            latitude=latitude,
            longitude=longitude,
            badge="",
            ticket_price="",
            is_open_now=is_open,
        ))

    return PaginatedAttractions(
        items=items,
        current_page=pagination.get("page", 1),
        total_pages=pagination.get("total_pages", 1),
        total_results=pagination.get("total_elements", len(items)),
        page_size=pagination.get("size", 20),
    )
