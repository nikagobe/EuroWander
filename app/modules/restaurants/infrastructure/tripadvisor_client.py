"""
TripAdvisor RapidAPI scraper client for restaurant search (tripadvisor-com1.p.rapidapi.com).
Handles restaurant search by geo ID with pagination via updateToken.
Also handles fetching detailed restaurant information by content ID.
"""

import logging
import re

import httpx

from app.modules.restaurants.domain.entities import (
    NearbyRestaurant,
    PaginatedRestaurants,
    Restaurant,
    RestaurantDetail,
    RestaurantPhoto,
    RestaurantReview,
)
from app.modules.restaurants.domain.interfaces import (
    RestaurantDetailProvider,
    RestaurantSearchProvider,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://tripadvisor-com1.p.rapidapi.com"
_RESTAURANTS_SEARCH_URL = f"{_BASE_URL}/restaurants/search"
_RESTAURANTS_DETAILS_URL = f"{_BASE_URL}/restaurants/details"


class TripAdvisorRestaurantClient(RestaurantSearchProvider, RestaurantDetailProvider):
    """Calls the RapidAPI TripAdvisor scraper for restaurant search and details."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-rapidapi-host": "tripadvisor-com1.p.rapidapi.com",
            "x-rapidapi-key": self._api_key,
        }

    async def search_restaurants(
        self,
        geo_id: int,
        page: int,
        currency: str,
        sort: str,
        update_token: str | None,
        query: str | None = None,
    ) -> PaginatedRestaurants:
        """
        Search restaurants by geo ID. Returns paginated results.
        For page > 1, pass the updateToken from the previous response.
        """
        params: dict[str, str | int] = {
            "geoId": geo_id,
            "language": "en_US",
            "currency": currency,
            "units": "kilometers",
            "sort": sort,
            "sortType": "desc",
        }

        # For pagination: page 1 uses no token; subsequent pages use updateToken
        if page and page > 1:
            params["page"] = page
        if update_token:
            params["updateToken"] = update_token

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                _RESTAURANTS_SEARCH_URL,
                params=params,
                headers=self._headers(),
                timeout=20.0,
            )
            logger.info(
                "TripAdvisor restaurants/search [%s]: geoId=%s page=%s, %d chars",
                response.status_code,
                geo_id,
                page,
                len(response.text),
            )
            if response.status_code >= 400:
                logger.error(
                    "TripAdvisor restaurants/search ERROR [%s]: geoId=%s\n"
                    "  Request URL: %s\n"
                    "  Response body: %s",
                    response.status_code, geo_id,
                    response.url,
                    response.text[:2000],
                )
            response.raise_for_status()
            payload: dict = response.json()

        return _parse_restaurants_response(payload)

    async def get_restaurant_details(
        self,
        content_id: str,
        currency: str,
    ) -> RestaurantDetail:
        """
        Fetch detailed information for a specific restaurant by its content ID.
        The content ID comes from /restaurants/search cardLink.route.typedParams.contentId.
        """
        params: dict[str, str] = {
            "contentId": content_id,
            "currency": currency,
            "units": "kilometers",
        }

        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(
                _RESTAURANTS_DETAILS_URL,
                params=params,
                headers=self._headers(),
                timeout=20.0,
            )
            logger.info(
                "TripAdvisor restaurants/details [%s]: contentId=%s, %d chars",
                response.status_code,
                content_id,
                len(response.text),
            )
            if response.status_code >= 400:
                logger.error(
                    "TripAdvisor restaurants/details ERROR [%s]: contentId=%s\n"
                    "  Response body: %s",
                    response.status_code, content_id, response.text[:2000],
                )
            response.raise_for_status()
            payload: dict = response.json()

        return _parse_restaurant_details_response(payload, content_id)


# ── Search Parsers ─────────────────────────────────────────────────────────────


def _parse_restaurants_response(payload: dict) -> PaginatedRestaurants:
    """Parse the RapidAPI TripAdvisor restaurants/search response."""
    data: dict = payload.get("data", {})
    meta: dict = payload.get("meta", {})

    # Find restaurant cards — they are AppPresentation_HorizontalCommerceCard items.
    # The API places them in a list under various keys (sections, content, etc.)
    cards: list[dict] = _find_restaurant_cards(data)

    items: list[Restaurant] = []
    for card in cards:
        restaurant = _parse_restaurant_card(card)
        if restaurant:
            items.append(restaurant)

    return PaginatedRestaurants(
        items=items,
        current_page=meta.get("currentPage", 1),
        total_pages=meta.get("totalPage", 1),
        total_results=meta.get("totalRecords", len(items)),
        page_size=meta.get("limit", 30),
        update_token=meta.get("updateToken", ""),
    )


def _find_restaurant_cards(data: dict) -> list[dict]:
    """
    Locate HorizontalCommerceCard entries from the response data.
    Checks known keys (sections, restaurants, content) and falls back to
    scanning all list-valued keys for card-typed dicts.
    """
    _KNOWN_KEYS = ("sections", "restaurants", "content", "cards")

    for key in _KNOWN_KEYS:
        candidate = data.get(key)
        if isinstance(candidate, list) and candidate:
            # Check if first non-empty item looks like a card
            if any(
                item.get("__typename") == "AppPresentation_HorizontalCommerceCard"
                for item in candidate[:5]
                if isinstance(item, dict)
            ):
                return [
                    item for item in candidate
                    if isinstance(item, dict)
                    and item.get("__typename") == "AppPresentation_HorizontalCommerceCard"
                ]

    # Fallback: scan all list values in data
    for value in data.values():
        if isinstance(value, list) and len(value) > 3:
            cards = [
                item for item in value
                if isinstance(item, dict)
                and item.get("__typename") == "AppPresentation_HorizontalCommerceCard"
            ]
            if cards:
                return cards

    return []


def _parse_restaurant_card(card: dict) -> Restaurant | None:
    """Parse a single restaurant card into a domain entity."""
    # Location ID
    save_id: dict = card.get("saveId", {})
    location_id: str = str(save_id.get("id", ""))
    if not location_id:
        return None

    # Name — strip numeric prefix like "4. "
    card_title: dict = card.get("cardTitle", {})
    raw_name: str = card_title.get("string", "")
    name: str = re.sub(r"^\d+\.\s*", "", raw_name).strip()
    if not name:
        return None

    # Cuisine / price info (e.g. "$$ - $$$ • Japanese • Bar • Vegetarian friendly")
    primary_info: dict = card.get("primaryInfo", {})
    cuisine: str = primary_info.get("text", "") if primary_info else ""

    # Extract price level from cuisine string
    price_level: str = _extract_price_level(cuisine)

    # Neighborhood
    secondary_info: dict = card.get("secondaryInfo", {})
    secondary_text: str = secondary_info.get("text", "") if secondary_info else ""
    # Remove "Open now • " prefix if present
    neighborhood: str = re.sub(r"^Open now\s*•?\s*", "", secondary_text).strip()

    # Rating
    bubble: dict = card.get("bubbleRating", {})
    rating: float = float(bubble.get("rating", 0) or 0)

    # Number of reviews — parse "(1,414)" → 1414
    reviews_str: str = bubble.get("numberReviews", {}).get("string", "")
    num_reviews: int = _parse_review_count(reviews_str)

    # Photo URL
    card_photo: dict = card.get("cardPhoto", {})
    sizes: dict = card_photo.get("sizes", {}) if card_photo else {}
    url_template: str = sizes.get("urlTemplate", "")
    photo_url: str = (
        url_template.replace("{width}", "800").replace("{height}", "600")
        if url_template
        else ""
    )

    # Badge (Travelers' Choice)
    badge_data: dict = card.get("badge", {})
    badge: str = badge_data.get("type", "") if badge_data else ""
    badge_year: str = badge_data.get("year", "") if badge_data else ""

    # Sponsored check
    labels: list[dict] = card.get("labels", [])
    is_sponsored: bool = any(
        lbl.get("__typename") == "AppPresentation_SponsoredLabel" for lbl in labels
    )

    return Restaurant(
        location_id=location_id,
        name=name,
        cuisine=cuisine,
        neighborhood=neighborhood,
        rating=rating,
        num_reviews=num_reviews,
        photo_url=photo_url,
        badge=badge,
        badge_year=badge_year,
        price_level=price_level,
        is_sponsored=is_sponsored,
    )


def _extract_price_level(cuisine_text: str) -> str:
    """Extract price level from the cuisine string (e.g. '$$$$', '$$ - $$$', '$')."""
    # Match common patterns: "$$$$", "$$ - $$$", "$"
    match = re.match(r"^\$[$\s-]*", cuisine_text)
    if match:
        return match.group(0).strip()
    return ""


def _parse_review_count(text: str) -> int:
    """Parse review count string like '(1,414)' into int."""
    digits = re.sub(r"[^\d]", "", text)
    return int(digits) if digits else 0


# ── Details Parsers ────────────────────────────────────────────────────────────


def _parse_restaurant_details_response(payload: dict, content_id: str) -> RestaurantDetail:
    """Parse the RapidAPI TripAdvisor restaurants/details response into domain entity."""
    data: dict = payload.get("data", {})
    container: dict = data.get("container", {})
    sections: list[dict] = data.get("sections", [])

    name: str = container.get("navTitle", "")

    # Extract sections by type
    overview: dict = _find_section(sections, "AppPresentation_PoiOverview")
    hours: dict = _find_section(sections, "AppPresentation_PoiHours")
    about: dict = _find_section(sections, "AppPresentation_PoiAbout")
    location: dict = _find_section(sections, "AppPresentation_PoiLocation")
    hero: dict = _find_section(sections, "AppPresentation_PoiHeroStandard")
    reviews_section: dict = _find_section(sections, "AppPresentation_PoiReviewsAndQA")
    nearby_section: dict = _find_nearby_restaurants_section(sections)

    # Overview data
    rating: float = float(overview.get("rating", 0) or 0)
    num_reviews: int = overview.get("numberReviews", 0) or 0

    # Ranking
    ranking_details: dict = overview.get("rankingDetailsV2", {})
    ranking_text_data: dict = ranking_details.get("text", {}) if ranking_details else {}
    ranking: str = re.sub(r"<[^>]+>", "", ranking_text_data.get("text", "")) if ranking_text_data else ""

    # Price level from tags
    tags: dict = overview.get("tagsV2", {})
    price_level: str = tags.get("text", "") if tags else ""

    # Contact links (website, phone)
    website: str = ""
    phone: str = ""
    contact_links: list[dict] = overview.get("contactLinks", []) or []
    for link_data in contact_links:
        link_type: str = link_data.get("linkType", "")
        link_obj: dict = link_data.get("link", {})
        if link_type == "WEBSITE":
            website = link_obj.get("externalUrl", "") if link_obj else ""
        elif link_type == "PHONE":
            raw_phone: str = link_obj.get("externalUrl", "") if link_obj else ""
            phone = raw_phone.replace("tel:", "").replace("%2B", "+").replace("%20", " ")

    # Hours
    hours_text: dict = hours.get("text", {})
    hours_status: str = hours_text.get("string", "") if hours_text else ""
    today_schedule_raw: list[dict] = hours.get("todaySchedule", []) or []
    today_schedule: list[str] = [
        s.get("string", "") for s in today_schedule_raw if s.get("string")
    ]

    # About section — description, serving, features
    description: str = ""
    serving: list[str] = []
    features: list[str] = []
    cuisines: list[str] = []
    about_content: list[dict] = about.get("nullableContent", []) or []
    for subsection in about_content:
        typename: str = subsection.get("__typename", "")
        if typename == "AppPresentation_CollapsibleTextSubsection":
            text_obj: dict = subsection.get("text", {})
            description = text_obj.get("string", "") if text_obj else ""
        elif typename == "AppPresentation_SmallTextListSubsection":
            title_obj: dict = subsection.get("title", {})
            title: str = title_obj.get("string", "") if title_obj else ""
            items_list: list[dict] = subsection.get("list", []) or []
            values: list[str] = [i.get("string", "") for i in items_list if i.get("string")]
            if title.lower() == "serving":
                serving = values
            elif title.lower() == "features":
                features = values
            elif title.lower() in ("cuisines", "cuisine"):
                cuisines = values

    # Location
    address_data: dict = location.get("address", {})
    address: str = address_data.get("address", "") if address_data else ""
    geo_point: dict = address_data.get("geoPoint", {}) if address_data else {}
    latitude: float = float(geo_point.get("latitude", 0) or 0)
    longitude: float = float(geo_point.get("longitude", 0) or 0)

    # Photos
    photos: list[RestaurantPhoto] = _parse_detail_photos(hero)

    # Reviews
    reviews: list[RestaurantReview] = _parse_detail_reviews(reviews_section)

    # Nearby restaurants
    nearby_restaurants: list[NearbyRestaurant] = _parse_nearby_restaurants(nearby_section)

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
        today_schedule=today_schedule,
        serving=serving,
        features=features,
        cuisines=cuisines,
        photos=photos,
        reviews=reviews,
        nearby_restaurants=nearby_restaurants,
    )


def _find_section(sections: list[dict], typename: str) -> dict:
    """Find the first section matching a given __typename."""
    for section in sections:
        if section.get("__typename") == typename:
            return section
    return {}


def _find_nearby_restaurants_section(sections: list[dict]) -> dict:
    """Find the nearby restaurants section (PoiNearbyLocations for restaurants)."""
    for section in sections:
        if (
            section.get("__typename") == "AppPresentation_PoiNearbyLocations"
            and "Restaurant" in (section.get("trackingTitle", "") or "")
        ):
            return section
    return {}


def _parse_detail_photos(hero: dict) -> list[RestaurantPhoto]:
    """Parse hero photos from the details response."""
    photos: list[RestaurantPhoto] = []
    hero_content: list[dict] = hero.get("heroContent", []) or []

    for media in hero_content:
        media_data: dict = media.get("data", {})
        if not media_data:
            continue

        caption: str = media_data.get("caption", "")
        size_dynamic: dict = media_data.get("photoSizeDynamic", {})
        if not size_dynamic:
            continue

        max_width: int = size_dynamic.get("maxWidth", 0)
        max_height: int = size_dynamic.get("maxHeight", 0)
        url_template: str = size_dynamic.get("urlTemplate", "")

        # Generate a reasonable-size URL for Flutter
        url: str = url_template.replace("{width}", "800").replace("{height}", "600") if url_template else ""
        if url:
            photos.append(RestaurantPhoto(
                url=url,
                caption=caption,
                width=max_width,
                height=max_height,
            ))

    return photos


def _parse_detail_reviews(reviews_section: dict) -> list[RestaurantReview]:
    """Parse review cards from the reviews section."""
    reviews: list[RestaurantReview] = []
    tabs: list[dict] = reviews_section.get("tabs", []) or []

    if not tabs:
        return reviews

    # First tab is usually the Reviews tab
    review_tab: dict = tabs[0] if tabs else {}
    content: list[dict] = review_tab.get("content", []) or []

    for item in content:
        if item.get("__typename") != "AppPresentation_ReviewCard":
            continue

        review_rating: float = float(item.get("reviewRating", 0) or 0)

        html_title: dict = item.get("htmlTitle", {})
        title: str = html_title.get("htmlString", "") if html_title else ""

        html_text: dict = item.get("htmlText", {})
        text: str = html_text.get("htmlString", "") if html_text else ""

        user_profile: dict = item.get("userProfile", {})
        author: str = user_profile.get("displayName", "") if user_profile else ""

        published_date: str = item.get("publishedDateMediumMonthYear", "")

        bubble_text: dict = item.get("bubbleRatingText", {})
        trip_type: str = bubble_text.get("text", "") if bubble_text else ""

        reviews.append(RestaurantReview(
            rating=review_rating,
            title=title,
            text=text,
            author=author,
            published_date=published_date,
            trip_type=trip_type,
        ))

    return reviews


def _parse_nearby_restaurants(nearby_section: dict) -> list[NearbyRestaurant]:
    """Parse nearby restaurant cards."""
    nearby: list[NearbyRestaurant] = []
    content: list[dict] = nearby_section.get("nonNullContent", []) or []

    for card in content:
        if card.get("__typename") != "AppPresentation_HorizontalMinimalCardWithBackground":
            continue

        card_title_obj: dict = card.get("cardTitle", {})
        name: str = card_title_obj.get("string", "") if card_title_obj else ""

        bubble: dict = card.get("bubbleRating", {})
        rating: float = float(bubble.get("rating", 0) or 0)
        reviews_str: str = bubble.get("numberReviews", {}).get("string", "") if bubble else ""
        num_reviews: int = _parse_review_count(reviews_str)

        distance_obj: dict = card.get("distance", {})
        distance: str = distance_obj.get("string", "") if distance_obj else ""

        primary_info: dict = card.get("primaryInfo", {})
        cuisine: str = primary_info.get("text", "") if primary_info else ""

        # Photo
        card_photo: dict = card.get("cardPhoto", {})
        sizes: dict = card_photo.get("sizes", {}) if card_photo else {}
        url_template: str = sizes.get("urlTemplate", "")
        photo_url: str = (
            url_template.replace("{width}", "400").replace("{height}", "300")
            if url_template
            else ""
        )

        # Content ID from card link
        card_link: dict = card.get("cardLink", {})
        route: dict = card_link.get("route", {}) if card_link else {}
        typed_params: dict = route.get("typedParams", {}) if route else {}
        cid: str = typed_params.get("contentId", "") if typed_params else ""

        if name:
            nearby.append(NearbyRestaurant(
                content_id=cid,
                name=name,
                rating=rating,
                num_reviews=num_reviews,
                distance=distance,
                cuisine=cuisine,
                photo_url=photo_url,
            ))

    return nearby
