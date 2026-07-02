from fastapi import APIRouter, Depends, Query

from app.config import settings
from app.modules.restaurants.application.services import RestaurantService
from app.modules.restaurants.infrastructure.tripadvisor_client import TripAdvisorRestaurantClient
from app.modules.restaurants.presentation.schemas import (
    PaginatedRestaurantResponse,
    PaginationMeta,
    RestaurantDetailResponse,
    RestaurantResponse,
)

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


def get_restaurant_service() -> RestaurantService:
    """
    Returns a RestaurantService wired with the RapidAPI TripAdvisor scraper client.
    Uses the same RAPIDAPI_KEY as hotels/attractions.
    """
    client = TripAdvisorRestaurantClient(api_key=settings.rapidapi_key)
    return RestaurantService(search_provider=client, detail_provider=client)


@router.get("/search", response_model=PaginatedRestaurantResponse)
async def search_restaurants(
    geo_id: int = Query(..., description="TripAdvisor geo ID (from /attractions/destinations)"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    currency: str = Query("EUR", description="Currency code (EUR, USD, GBP…)"),
    sort: str = Query("POPULARITY", description="Sort: POPULARITY or RELEVANCE"),
    update_token: str | None = Query(None, description="Pagination token from previous response (for page > 1)"),
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
    content_id: str = Query(..., description="Restaurant content ID (from /restaurants/search results)"),
    currency: str = Query("EUR", description="Currency code (EUR, USD, GBP…)"),
    service: RestaurantService = Depends(get_restaurant_service),
) -> RestaurantDetailResponse:
    """
    Get full details for a specific restaurant.

    **Flutter flow:**
    1. User taps a restaurant from search results
    2. Pass the `content_id` from the search response
       (found in `data → restaurants → cardLink → route → typedParams → contentId`)
    3. Display detail page with photos, reviews, hours, address, map coordinates

    **Returns:** Name, rating, ranking, description, address, coordinates,
    phone, website, opening hours, features, photos, reviews, and nearby restaurants.
    """
    detail = await service.get_restaurant_details(
        content_id=content_id,
        currency=currency,
    )
    return RestaurantDetailResponse.from_entity(detail)
