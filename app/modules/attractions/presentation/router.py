import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.modules.attractions.application.services import AttractionService
from app.modules.attractions.infrastructure.terra_client import TerraAttractionDetailClient
from app.modules.attractions.infrastructure.tripadvisor_client import TripAdvisorScraperClient
from app.modules.attractions.presentation.schemas import (
    AttractionDestinationResponse,
    AttractionDetailResponse,
    AttractionResponse,
    AttractionReviewResponse,
    NearbyAttractionCardResponse,
    NearbyRestaurantCardResponse,
    PaginatedAttractionResponse,
    PaginationMeta,
)

router = APIRouter(prefix="/attractions", tags=["attractions"])


def get_attraction_service() -> AttractionService:
    """
    Returns an AttractionService wired with:
    - RapidAPI scraper for search/destinations (works well for listing)
    - Terra API for details (fast, reliable, official)
    """
    scraper_client = TripAdvisorScraperClient(api_key=settings.rapidapi_key)
    terra_client = TerraAttractionDetailClient(api_key=settings.tripadvisor_key)
    return AttractionService(
        destination_provider=scraper_client,
        search_provider=scraper_client,
        detail_provider=terra_client,
    )


def get_terra_client() -> TerraAttractionDetailClient:
    """Direct access to Terra client for reviews/nearby endpoints."""
    return TerraAttractionDetailClient(api_key=settings.tripadvisor_key)


@router.get("/destinations", response_model=list[AttractionDestinationResponse])
async def search_destinations(
    query: str = Query(..., min_length=2, description="City name search (e.g. 'Paris', 'Berlin')"),
    service: AttractionService = Depends(get_attraction_service),
) -> list[AttractionDestinationResponse]:
    """
    Autocomplete city search for attractions.

    - `query`: Free-text city name. Minimum 2 characters.
    - Returns only **cities** (filters out hotels, restaurants, etc.).
    - Use the returned `geo_id` for the `/attractions/search` endpoint.

    **Flutter flow:** User types city name → show dropdown → user picks a city → use `geo_id`.
    """
    destinations = await service.search_destinations(query)
    return [AttractionDestinationResponse.from_entity(d) for d in destinations]


@router.get("/search", response_model=PaginatedAttractionResponse)
async def search_attractions(
    geo_id: int = Query(..., description="TripAdvisor geo ID (from /attractions/destinations)"),
    start_date: str = Query(..., description="Trip start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Trip end date (YYYY-MM-DD)"),
    adults: int = Query(1, ge=1, description="Number of adults"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    currency: str = Query("EUR", description="Currency code (EUR, USD, GBP…)"),
    sort: str = Query("TRAVELER_FAVORITE_V2", description="Sort: TRAVELER_FAVORITE_V2 or TRAVELER_RANKED"),
    query: str | None = Query(None, min_length=2, description="Optional keyword to filter attractions by name (e.g. 'Eiffel', 'Colosseum')"),
    service: AttractionService = Depends(get_attraction_service),
) -> PaginatedAttractionResponse:
    """
    Search attractions in a city — paginated, sorted by traveler favorites.

    **Flutter flow:**
    1. User picks city from `/attractions/destinations` → gets `geo_id`
    2. Call this endpoint with `geo_id` + trip dates
    3. Paginate with `page` param for infinite scroll (~30 results per page)

    **Sort options:**
    - `TRAVELER_FAVORITE_V2` (default) — most popular
    - `TRAVELER_RANKED` — highest rated

    Returns name, category, rating, reviews, photo, coordinates, badge, and ticket price.
    """
    result = await service.search_attractions(
        geo_id=geo_id,
        start_date=start_date,
        end_date=end_date,
        adults=adults,
        page=page,
        currency=currency,
        sort=sort,
        query=query,
    )
    return PaginatedAttractionResponse(
        data=[AttractionResponse.from_entity(a) for a in result.items],
        pagination=PaginationMeta(
            current_page=result.current_page,
            total_pages=result.total_pages,
            total_results=result.total_results,
            page_size=result.page_size,
        ),
    )


@router.get("/details/{content_id}", response_model=AttractionDetailResponse)
async def get_attraction_details(
    content_id: str,
    start_date: str = Query(..., description="Trip start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Trip end date (YYYY-MM-DD)"),
    currency: str = Query("EUR", description="Currency code (EUR, USD, GBP…)"),
    adults: int = Query(1, ge=1, description="Number of adults"),
    service: AttractionService = Depends(get_attraction_service),
) -> AttractionDetailResponse:
    """
    Get full details for a single attraction (powered by Terra API).

    - `content_id`: Attraction ID from search results (`location_id` field).
    - Returns name, description, rating, address, hours, photos.
    - Reviews and nearby are separate endpoints for better performance.

    **Flutter flow:**
    1. User taps an attraction from `/attractions/search` results
    2. Call this endpoint with the `location_id` as `content_id`
    3. Render the detail screen with all returned data
    4. Lazy-load reviews via `/attractions/details/{id}/reviews`
    5. Lazy-load nearby via `/attractions/details/{id}/nearby`
    """
    try:
        detail = await service.get_attraction_details(
            content_id=content_id,
            start_date=start_date,
            end_date=end_date,
            currency=currency,
            adults=adults,
        )
    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=504,
            detail="Attraction details request timed out. Please try again.",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream API error: {exc.response.status_code}",
        )
    return AttractionDetailResponse.from_entity(detail)


@router.get("/details/{content_id}/reviews", response_model=list[AttractionReviewResponse])
async def get_attraction_reviews(
    content_id: str,
    language: str = Query("en", description="Review language (en, fr, de, es…)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(5, ge=1, le=20, description="Reviews per page"),
    terra: TerraAttractionDetailClient = Depends(get_terra_client),
) -> list[AttractionReviewResponse]:
    """
    Get reviews for an attraction (separate from details for faster loading).

    - `content_id`: Attraction location ID.
    - Paginated — Flutter can lazy-load more reviews on scroll.

    **Flutter flow:** After detail screen renders, call this to fill the reviews section.
    """
    reviews = await terra.get_reviews(
        location_id=content_id,
        language=language,
        page=page,
        size=size,
    )
    return [
        AttractionReviewResponse(
            rating=r.rating,
            title=r.title,
            text=r.text,
            author=r.author,
            published_date=r.published_date,
            trip_type=r.trip_type,
        )
        for r in reviews
    ]


@router.get("/details/{content_id}/nearby", response_model=dict)
async def get_nearby_locations(
    content_id: str,
    category: str | None = Query(None, description="Filter: ATTRACTION or RESTAURANT"),
    size: int = Query(10, ge=1, le=20, description="Number of results"),
    terra: TerraAttractionDetailClient = Depends(get_terra_client),
) -> dict:
    """
    Get nearby attractions/restaurants for a location.

    - `content_id`: Attraction location ID (used as center point).
    - `category`: Optional filter — ATTRACTION or RESTAURANT.

    **Flutter flow:** Show nearby places on the detail screen's map or list section.
    """
    results = await terra.get_nearby(
        location_id=content_id,
        category=category,
        size=size,
    )

    items: list[dict] = []
    for entry in results:
        loc: dict = entry.get("location", {})
        if not loc:
            continue

        names: list[dict] = loc.get("names", [])
        name: str = ""
        for n in names:
            if n.get("primary"):
                name = n.get("value", "")
                break
        if not name and names:
            name = names[0].get("value", "")

        traveler_ratings: dict = loc.get("traveler_ratings", {})
        overall: dict = traveler_ratings.get("overall", {})

        categories: list[dict] = loc.get("categories", [])
        cat_name: str = categories[0].get("display_name", "") if categories else ""

        photo_data: dict = entry.get("photo", {}) or {}
        photo_info: dict = photo_data.get("photo", {}) or {}
        photo_url: str = photo_info.get("original_size_url", "")

        distance_km: float = entry.get("distance_kilometers", 0) or 0

        items.append({
            "location_id": str(loc.get("id", "")),
            "name": name,
            "rating": float(overall.get("rating", 0) or 0),
            "num_reviews": int(overall.get("count", 0) or 0),
            "distance": f"{distance_km:.1f} km",
            "category": cat_name,
            "photo_url": photo_url,
        })

    return {"data": items, "total": len(items)}
