import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import settings
from app.modules.restaurants.application.services import RestaurantService
from app.modules.restaurants.infrastructure.terra_client import TerraRestaurantDetailClient
from app.modules.restaurants.infrastructure.tripadvisor_client import TripAdvisorRestaurantClient
from app.modules.restaurants.presentation.schemas import (
    PaginatedRestaurantResponse,
    PaginationMeta,
    RestaurantDetailResponse,
    RestaurantResponse,
    RestaurantReviewResponse,
)

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


def get_restaurant_service() -> RestaurantService:
    """
    Returns a RestaurantService wired with:
    - RapidAPI scraper for search (pagination with updateToken)
    - Terra API for details (fast, reliable, official)
    """
    scraper_client = TripAdvisorRestaurantClient(api_key=settings.tripadvisor_rapidapi_key)
    terra_client = TerraRestaurantDetailClient(api_key=settings.tripadvisor_key)
    return RestaurantService(search_provider=scraper_client, detail_provider=terra_client)


def get_terra_restaurant_client() -> TerraRestaurantDetailClient:
    """Direct access to Terra client for reviews endpoint."""
    return TerraRestaurantDetailClient(api_key=settings.tripadvisor_key)


@router.get("/search", response_model=PaginatedRestaurantResponse)
async def search_restaurants(
    geo_id: int = Query(..., description="TripAdvisor geo ID (from /attractions/destinations)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    currency: str = Query("EUR", description="Currency code (EUR, USD, GBP…)"),
    sort: str = Query("POPULARITY", description="Sort: POPULARITY or RELEVANCE"),
    update_token: str | None = Query(None, description="Pagination token from previous response (for page > 1)"),
    query: str | None = Query(None, min_length=2, description="Optional keyword to filter restaurants by name (e.g. 'Sushi', 'Pizza')"),
    service: RestaurantService = Depends(get_restaurant_service),
) -> PaginatedRestaurantResponse:
    """
    Search restaurants in a city — paginated, sorted by popularity.

    **Flutter flow:**
    1. User picks city from `/attractions/destinations` → gets `geo_id`
    2. Call this endpoint with `geo_id`
    3. For next pages, pass `update_token` from the previous response + increment `page`

    **Sort options:**
    - `POPULARITY` (default) — most popular
    - `RELEVANCE` — most relevant

    Returns name, cuisine, rating, reviews, photo, badge, price level (~30 results per page).
    """
    result = await service.search_restaurants(
        geo_id=geo_id,
        page=page,
        currency=currency,
        sort=sort,
        update_token=update_token,
        query=query,
    )
    return PaginatedRestaurantResponse(
        data=[RestaurantResponse.from_entity(r) for r in result.items],
        pagination=PaginationMeta(
            current_page=result.current_page,
            total_pages=result.total_pages,
            total_results=result.total_results,
            page_size=result.page_size,
            update_token=result.update_token,
        ),
    )


@router.get("/details", response_model=RestaurantDetailResponse)
async def get_restaurant_details(
    content_id: str = Query(..., description="Restaurant content ID (location_id from search results)"),
    currency: str = Query("EUR", description="Currency code (EUR, USD, GBP…)"),
    service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantDetailResponse:
    """
    Get full details for a specific restaurant (powered by Terra API).

    - Returns name, rating, description, address, coordinates, hours, photos.
    - Reviews are a separate endpoint for lazy-loading.

    **Flutter flow:**
    1. User taps a restaurant from search results
    2. Pass `content_id` (the `location_id` from search)
    3. Display detail page
    4. Lazy-load reviews via `/restaurants/details/reviews`
    """
    try:
        detail = await service.get_restaurant_details(
            content_id=content_id,
            currency=currency,
        )
    except httpx.ReadTimeout:
        raise HTTPException(
            status_code=504,
            detail="Restaurant details request timed out. Please try again.",
        )
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream API error: {exc.response.status_code}",
        )
    return RestaurantDetailResponse.from_entity(detail)


@router.get("/details/reviews", response_model=list[RestaurantReviewResponse])
async def get_restaurant_reviews(
    content_id: str = Query(..., description="Restaurant location ID"),
    language: str = Query("en", description="Review language (en, fr, de, es…)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(5, ge=1, le=20, description="Reviews per page"),
    terra: TerraRestaurantDetailClient = Depends(get_terra_restaurant_client),
) -> list[RestaurantReviewResponse]:
    """
    Get reviews for a restaurant (separate from details for faster loading).

    - `content_id`: Restaurant location ID.
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
        RestaurantReviewResponse(
            rating=r.rating,
            title=r.title,
            text=r.text,
            author=r.author,
            published_date=r.published_date,
            trip_type=r.trip_type,
        )
        for r in reviews
    ]


@router.get("/details/nearby", response_model=dict)
async def get_nearby_restaurants(
    content_id: str = Query(..., description="Restaurant location ID (used as center point)"),
    size: int = Query(10, ge=1, le=20, description="Number of results"),
    terra: TerraRestaurantDetailClient = Depends(get_terra_restaurant_client),
) -> dict:
    """
    Get nearby restaurants for a location.

    - `content_id`: Restaurant location ID (used as center point for radius search).
    - Returns up to `size` nearby restaurants within 5 km.

    **Flutter flow:** Show nearby restaurants on the detail screen's map or "More nearby" section.
    """
    results = await terra.get_nearby(
        location_id=content_id,
        category="RESTAURANT",
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
        cuisine: str = ", ".join(c.get("display_name", "") for c in categories[:3] if c.get("display_name"))

        photo_data: dict = entry.get("photo", {}) or {}
        photo_info: dict = photo_data.get("photo", {}) or {}
        photo_url: str = photo_info.get("original_size_url", "")

        distance_km: float = entry.get("distance_kilometers", 0) or 0
        price_level: str = loc.get("price_level", "") or ""

        items.append({
            "location_id": str(loc.get("id", "")),
            "name": name,
            "rating": float(overall.get("rating", 0) or 0),
            "num_reviews": int(overall.get("count", 0) or 0),
            "distance": f"{distance_km:.1f} km",
            "cuisine": cuisine,
            "price_level": price_level,
            "photo_url": photo_url,
        })

    return {"data": items, "total": len(items)}

