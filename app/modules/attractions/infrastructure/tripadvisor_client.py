"""
TripAdvisor RapidAPI scraper client (tripadvisor-com1.p.rapidapi.com).
Handles autocomplete for city destinations, attraction search, and attraction details.
"""

import logging
import re

import httpx

from app.modules.attractions.domain.entities import (
    Attraction,
    AttractionDestination,
    AttractionDetail,
    AttractionPhoto,
    AttractionReview,
    NearbyAttractionCard,
    NearbyRestaurantCard,
    PaginatedAttractions,
)
from app.modules.attractions.domain.interfaces import (
    AttractionDestinationProvider,
    AttractionDetailProvider,
    AttractionSearchProvider,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://tripadvisor-com1.p.rapidapi.com"
_AUTOCOMPLETE_URL = f"{_BASE_URL}/auto-complete"
_ATTRACTIONS_SEARCH_URL = f"{_BASE_URL}/attractions/search"
_ATTRACTIONS_DETAILS_URL = f"{_BASE_URL}/attractions/details"


class TripAdvisorScraperClient(
    AttractionDestinationProvider, AttractionSearchProvider, AttractionDetailProvider
):
    """Calls the RapidAPI TripAdvisor scraper for destination autocomplete, attraction search, and details."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-rapidapi-host": "tripadvisor-com1.p.rapidapi.com",
            "x-rapidapi-key": self._api_key,
        }

    # ── Autocomplete ──────────────────────────────────────────────────────────

    async def search_destinations(self, query: str) -> list[AttractionDestination]:
        """
        Query TripAdvisor autocomplete and return only CITY results.
        Filters out hotels, restaurants, rescue queries, etc.
        """
        params: dict[str, str] = {"query": query}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                _AUTOCOMPLETE_URL,
                params=params,
                headers=self._headers(),
                timeout=15.0,
            )
            logger.info(
                "TripAdvisor autocomplete [%s]: query=%r, results=%d chars",
                response.status_code,
                query,
                len(response.text),
            )
            response.raise_for_status()
            payload: dict = response.json()

        return _parse_autocomplete_cities(payload)

    # ── Attraction Search ─────────────────────────────────────────────────────

    async def search_attractions(
        self,
        geo_id: int,
        start_date: str,
        end_date: str,
        adults: int,
        page: int,
        currency: str,
        sort: str,
    ) -> PaginatedAttractions:
        """
        Search attractions by geo ID. Returns paginated results sorted by traveler favorites.
        """
        params: dict[str, str | int] = {
            "geoId": geo_id,
            "startDate": start_date,
            "endDate": end_date,
            "adults": adults,
            "page": page,
            "currency": currency,
            "sort": sort,
            "sortType": "desc",
            "units": "kilometers",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                _ATTRACTIONS_SEARCH_URL,
                params=params,
                headers=self._headers(),
                timeout=20.0,
            )
            logger.info(
                "TripAdvisor attractions/search [%s]: geoId=%s page=%s, %d chars",
                response.status_code,
                geo_id,
                page,
                len(response.text),
            )
            response.raise_for_status()
            payload: dict = response.json()

        return _parse_attractions_response(payload)

    # ── Attraction Details ────────────────────────────────────────────────────

    async def get_attraction_details(
        self,
        content_id: str,
        start_date: str,
        end_date: str,
        currency: str,
        adults: int,
    ) -> AttractionDetail:
        """Fetch attraction details from TripAdvisor RapidAPI."""
        params: dict[str, str | int] = {
            "contentId": content_id,
            "startDate": start_date,
            "endDate": end_date,
            "currency": currency,
            "units": "kilometers",
            "adults": adults,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                _ATTRACTIONS_DETAILS_URL,
                params=params,
                headers=self._headers(),
                timeout=20.0,
            )
            logger.info(
                "TripAdvisor attractions/details [%s]: contentId=%s, %d chars",
                response.status_code,
                content_id,
                len(response.text),
            )
            response.raise_for_status()
            payload: dict = response.json()

        return _parse_attraction_detail(payload, content_id)


# ── Parsers ────────────────────────────────────────────────────────────────────


def _parse_attractions_response(payload: dict) -> PaginatedAttractions:
    """Parse the RapidAPI TripAdvisor attractions/search response."""
    data: dict = payload.get("data", {})
    meta: dict = payload.get("meta", {})

    # Build lat/lng lookup from map pins
    coords_map: dict[str, tuple[float, float]] = _build_coords_map(data)

    # Parse attraction cards
    cards: list[dict] = data.get("attractions", [])
    items: list[Attraction] = []

    for card in cards:
        attraction = _parse_attraction_card(card, coords_map)
        if attraction:
            items.append(attraction)

    return PaginatedAttractions(
        items=items,
        current_page=meta.get("currentPage", 1),
        total_pages=meta.get("totalPage", 1),
        total_results=meta.get("totalRecords", len(items)),
        page_size=meta.get("limit", 30),
    )


def _build_coords_map(data: dict) -> dict[str, tuple[float, float]]:
    """Extract lat/lng from mapSections pins, keyed by location ID."""
    coords: dict[str, tuple[float, float]] = {}
    map_sections: list[dict] = data.get("mapSections", [])

    for section in map_sections:
        pins: list[dict] = section.get("pins", [])
        for pin in pins:
            geo_point: dict = pin.get("geoPoint", {})
            save_id: dict = pin.get("saveId", {})
            loc_id: str = str(save_id.get("id", ""))
            lat = geo_point.get("latitude", 0.0)
            lon = geo_point.get("longitude", 0.0)
            if loc_id and lat and lon:
                coords[loc_id] = (float(lat), float(lon))

    return coords


def _parse_attraction_card(
    card: dict, coords_map: dict[str, tuple[float, float]]
) -> Attraction | None:
    """Parse a single attraction card into a domain entity."""
    # Location ID
    save_id: dict = card.get("saveId", {})
    location_id: str = str(save_id.get("id", ""))
    if not location_id:
        return None

    # Name — strip numeric prefix like "1. "
    card_title: dict = card.get("cardTitle", {})
    raw_name: str = card_title.get("string", "")
    name: str = re.sub(r"^\d+\.\s*", "", raw_name).strip()
    if not name:
        return None

    # Category
    primary_info: dict = card.get("primaryInfo", {})
    category: str = primary_info.get("text", "") if primary_info else ""

    # Neighborhood / "Open now"
    secondary_info: dict = card.get("secondaryInfo", {})
    secondary_text: str = secondary_info.get("text", "") if secondary_info else ""
    is_open_now: bool = secondary_text.lower() == "open now"
    neighborhood: str = secondary_text if not is_open_now else ""

    # Rating
    bubble: dict = card.get("bubbleRating", {})
    rating: float = float(bubble.get("rating", 0) or 0)

    # Number of reviews — parse "(14,062)" → 14062
    reviews_str: str = bubble.get("numberReviews", {}).get("string", "")
    num_reviews: int = _parse_review_count(reviews_str)

    # Photo URL
    card_photo: dict = card.get("cardPhoto", {})
    sizes: dict = card_photo.get("sizes", {}) if card_photo else {}
    url_template: str = sizes.get("urlTemplate", "")
    photo_url: str = url_template.replace("{width}", "800").replace("{height}", "600") if url_template else ""

    # Coordinates from map pins
    lat, lon = coords_map.get(location_id, (0.0, 0.0))

    # Badge (Travelers' Choice, Best of the Best)
    badge_data: dict = card.get("badge", {})
    badge: str = badge_data.get("type", "") if badge_data else ""

    # Ticket price
    merch: dict = card.get("merchandisingText", {})
    ticket_price: str = _strip_html(merch.get("htmlString", "")) if merch else ""

    return Attraction(
        location_id=location_id,
        name=name,
        category=category,
        neighborhood=neighborhood,
        rating=rating,
        num_reviews=num_reviews,
        photo_url=photo_url,
        latitude=lat,
        longitude=lon,
        badge=badge,
        ticket_price=ticket_price,
        is_open_now=is_open_now,
    )


def _parse_review_count(text: str) -> int:
    """Parse review count string like '(14,062)' into int."""
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


# ── Attraction Details Parser ──────────────────────────────────────────────────


def _parse_attraction_detail(payload: dict, content_id: str) -> AttractionDetail:
    """Parse the full attractions/details API response into domain entity."""
    data: dict = payload.get("data", {})
    sections: list[dict] = data.get("sections", [])

    name: str = ""
    rating: float = 0.0
    num_reviews: int = 0
    ranking: str = ""
    category: str = ""
    description: str = ""
    address: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    phone: str = ""
    website: str = ""
    hours_status: str = ""
    today_schedule: list[str] = []
    about_items: list[str] = []
    photos: list[AttractionPhoto] = []
    reviews: list[AttractionReview] = []
    nearby_attractions: list[NearbyAttractionCard] = []
    nearby_restaurants: list[NearbyRestaurantCard] = []

    for section in sections:
        typename: str = section.get("__typename", "")

        if typename == "AppPresentation_PoiHeroStandard":
            photos = _parse_hero_photos(section)

        elif typename == "AppPresentation_PoiOverview":
            name = section.get("name", "")
            rating = float(section.get("rating", 0) or 0)
            num_reviews = int(section.get("numberReviews", 0) or 0)
            # Category from tags
            tags_obj: dict = section.get("tagsV2", {})
            category = tags_obj.get("text", "") if tags_obj else ""
            # Ranking
            ranking_obj: dict = section.get("rankingDetailsV2", {})
            if ranking_obj:
                ranking_text_obj: dict = ranking_obj.get("text", {})
                ranking = _strip_html(ranking_text_obj.get("text", "")) if ranking_text_obj else ""
            # Contact links (website, phone)
            contact_links: list[dict] = section.get("contactLinks", [])
            for contact in contact_links:
                link_type: str = contact.get("linkType", "")
                link_obj: dict = contact.get("link", {})
                if link_type == "WEBSITE":
                    website = link_obj.get("externalUrl", "") if link_obj else ""
                elif link_type == "PHONE":
                    raw_phone: str = link_obj.get("externalUrl", "") if link_obj else ""
                    phone = raw_phone.replace("tel:", "").replace("%20", " ").replace("%2B", "+")

        elif typename in ("AppPresentation_PoiHoursV2", "AppPresentation_PoiHours"):
            status_obj: dict = section.get("statusText", {})
            hours_status = status_obj.get("string", "") if status_obj else ""
            schedule_list: list[dict] = section.get("todaySchedule", [])
            today_schedule = [
                s.get("string", "") for s in schedule_list if s.get("string")
            ]

        elif typename == "AppPresentation_PoiAbout":
            content_list: list[dict] = section.get("nullableContent", []) or []
            for item in content_list:
                title_obj: dict = item.get("titleWithStyle", {})
                if title_obj:
                    text_obj: dict = title_obj.get("text", {})
                    text_val: str = text_obj.get("string", "") if text_obj else ""
                    if text_val:
                        about_items.append(text_val)

        elif typename in ("AppPresentation_PoiLocationV2", "AppPresentation_PoiLocation"):
            addr_obj: dict = section.get("address", {})
            if addr_obj:
                address = addr_obj.get("address", "")
                geo_point: dict = addr_obj.get("geoPoint", {})
                latitude = float(geo_point.get("latitude", 0) or 0)
                longitude = float(geo_point.get("longitude", 0) or 0)

        elif typename == "AppPresentation_ContactsSection":
            contacts: list[dict] = section.get("contacts", [])
            for contact in contacts:
                link_type = contact.get("linkType", "")
                link_obj = contact.get("link", {})
                if link_type == "WEBSITE" and not website:
                    website = link_obj.get("externalUrl", "") if link_obj else ""
                elif link_type == "PHONE" and not phone:
                    raw_phone = link_obj.get("externalUrl", "") if link_obj else ""
                    phone = raw_phone.replace("tel:", "").replace("%20", " ").replace("%2B", "+")

        elif typename == "AppPresentation_PoiNearbyLocations":
            tracking_title: str = section.get("trackingTitle", "")
            content_cards: list[dict] = section.get("nonNullContent", []) or []
            if "Restaurant" in tracking_title:
                nearby_restaurants = _parse_nearby_restaurant_cards(content_cards)
            elif "Attraction" in tracking_title:
                nearby_attractions = _parse_nearby_attraction_cards(content_cards)

        elif typename == "AppPresentation_UserReviewSection":
            review = _parse_review_section(section)
            if review:
                reviews.append(review)

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
        today_schedule=today_schedule,
        about_items=about_items,
        photos=photos,
        reviews=reviews,
        nearby_attractions=nearby_attractions,
        nearby_restaurants=nearby_restaurants,
    )


def _parse_hero_photos(section: dict) -> list[AttractionPhoto]:
    """Parse hero section photos."""
    photos: list[AttractionPhoto] = []
    hero_content: list[dict] = section.get("heroContent", [])

    for media in hero_content:
        data: dict = media.get("data", {})
        if data.get("__typename") != "Media_PhotoResult":
            continue
        photo_dynamic: dict = data.get("photoSizeDynamic", {})
        url_template: str = photo_dynamic.get("urlTemplate", "")
        max_w: int = photo_dynamic.get("maxWidth", 0)
        max_h: int = photo_dynamic.get("maxHeight", 0)
        if not url_template:
            continue
        url: str = url_template.replace("{width}", "800").replace("{height}", "600")
        caption: str = data.get("caption", "")
        photos.append(AttractionPhoto(url=url, caption=caption, width=max_w, height=max_h))

    return photos


def _parse_review_section(section: dict) -> AttractionReview | None:
    """Parse a single UserReviewSection into a domain review entity."""
    bubble: dict = section.get("bubbleRating", {})
    rating: float = float(bubble.get("rating", 0) or 0)

    title_obj: dict = section.get("htmlTitle", {})
    title: str = _strip_html(title_obj.get("htmlString", "")) if title_obj else ""

    text_obj: dict = section.get("htmlText", {})
    text: str = _strip_html(text_obj.get("htmlString", "")) if text_obj else ""

    if not text and not title:
        return None

    profile: dict = section.get("userProfile", {})
    author: str = profile.get("displayName", "") if profile else ""

    pub_date_obj: dict = section.get("publishedDate", {})
    published_date: str = pub_date_obj.get("string", "") if pub_date_obj else ""

    trip_type_obj: dict = section.get("tripTypeValue", {})
    trip_type: str = trip_type_obj.get("string", "") if trip_type_obj else ""

    return AttractionReview(
        rating=rating,
        title=title,
        text=text,
        author=author,
        published_date=published_date,
        trip_type=trip_type,
    )


def _parse_nearby_restaurant_cards(cards: list[dict]) -> list[NearbyRestaurantCard]:
    """Parse nearby restaurant cards from the details response."""
    results: list[NearbyRestaurantCard] = []
    for card in cards:
        card_link: dict = card.get("cardLink", {})
        route: dict = card_link.get("route", {}) if card_link else {}
        params: dict = route.get("params", {}) if route else {}
        cid: str = str(params.get("contentId", ""))
        if not cid:
            continue

        title_obj: dict = card.get("cardTitle", {})
        name: str = title_obj.get("string", "") if title_obj else ""

        bubble: dict = card.get("bubbleRating", {})
        rating: float = float(bubble.get("rating", 0) or 0)
        reviews_str: str = bubble.get("numberReviews", {}).get("string", "") if bubble else ""
        num_reviews: int = _parse_review_count(reviews_str)

        dist_obj: dict = card.get("distance", {})
        distance: str = dist_obj.get("string", "") if dist_obj else ""

        primary_info: dict = card.get("primaryInfo", {})
        cuisine: str = primary_info.get("text", "") if primary_info else ""

        card_photo: dict = card.get("cardPhoto", {})
        sizes: dict = card_photo.get("sizes", {}) if card_photo else {}
        url_template: str = sizes.get("urlTemplate", "")
        photo_url: str = url_template.replace("{width}", "600").replace("{height}", "400") if url_template else ""

        results.append(NearbyRestaurantCard(
            content_id=cid,
            name=name,
            rating=rating,
            num_reviews=num_reviews,
            distance=distance,
            cuisine=cuisine,
            photo_url=photo_url,
        ))
    return results


def _parse_nearby_attraction_cards(cards: list[dict]) -> list[NearbyAttractionCard]:
    """Parse nearby attraction cards from the details response."""
    results: list[NearbyAttractionCard] = []
    for card in cards:
        card_link: dict = card.get("cardLink", {})
        route: dict = card_link.get("route", {}) if card_link else {}
        params: dict = route.get("params", {}) if route else {}
        cid: str = str(params.get("contentId", ""))
        if not cid:
            continue

        title_obj: dict = card.get("cardTitle", {})
        name: str = title_obj.get("string", "") if title_obj else ""

        bubble: dict = card.get("bubbleRating", {})
        rating: float = float(bubble.get("rating", 0) or 0)
        reviews_str: str = bubble.get("numberReviews", {}).get("string", "") if bubble else ""
        num_reviews: int = _parse_review_count(reviews_str)

        dist_obj: dict = card.get("distance", {})
        distance: str = dist_obj.get("string", "") if dist_obj else ""

        primary_info: dict = card.get("primaryInfo", {})
        category: str = primary_info.get("text", "") if primary_info else ""

        card_photo: dict = card.get("cardPhoto", {})
        sizes: dict = card_photo.get("sizes", {}) if card_photo else {}
        url_template: str = sizes.get("urlTemplate", "")
        photo_url: str = url_template.replace("{width}", "600").replace("{height}", "400") if url_template else ""

        results.append(NearbyAttractionCard(
            content_id=cid,
            name=name,
            rating=rating,
            num_reviews=num_reviews,
            distance=distance,
            category=category,
            photo_url=photo_url,
        ))
    return results


# ── Autocomplete parsers ───────────────────────────────────────────────────────


def _parse_autocomplete_cities(payload: dict) -> list[AttractionDestination]:
    """
    Parse the RapidAPI TripAdvisor autocomplete response.
    Only returns results where placeType is CITY or ISLAND (geographic destinations).
    """
    data: list[dict] = payload.get("data", [])
    results: list[AttractionDestination] = []

    _VALID_PLACE_TYPES = {"CITY", "ISLAND", "MUNICIPALITY", "REGION"}

    for item in data:
        tracking: dict = item.get("trackingItems", {})
        place_type: str = tracking.get("placeType") or ""

        if place_type.upper() not in _VALID_PLACE_TYPES:
            continue

        geo_id: int | None = item.get("geoId") or tracking.get("locationId")
        if not geo_id:
            continue

        # Name: strip HTML tags from heading
        heading: dict = item.get("heading", {})
        raw_name: str = heading.get("htmlString", "")
        name: str = _strip_html(raw_name)
        if not name:
            name = tracking.get("text", "")

        # Secondary text (region, country)
        secondary_obj: dict = item.get("secondaryTextLineOne", {})
        secondary_text: str = secondary_obj.get("string", "") if secondary_obj else ""

        # Image URL (some cities have a photo)
        image_url: str = ""
        graphic: dict = item.get("graphic", {})
        if graphic.get("__typename") == "AppPresentation_TypeaheadImage":
            image_data: dict = graphic.get("image", {})
            sizes: dict = image_data.get("sizes", {})
            url_template: str = sizes.get("urlTemplate", "")
            if url_template:
                image_url = url_template.replace("{width}", "600").replace("{height}", "400")

        results.append(
            AttractionDestination(
                geo_id=int(geo_id),
                name=name,
                secondary_text=secondary_text,
                image_url=image_url,
            )
        )

    return results


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text).strip()
