from fastapi import APIRouter, Depends, Query

from app.config import settings
from app.modules.attractions.application.services import AttractionService
from app.modules.attractions.infrastructure.tripadvisor_client import TripAdvisorScraperClient
from app.modules.attractions.presentation.schemas import (
    AttractionDestinationResponse,
    AttractionDetailResponse,
    AttractionResponse,
    PaginatedAttractionResponse,
    PaginationMeta,
)

router = APIRouter(prefix="/attractions", tags=["attractions"])


def get_attraction_service() -> AttractionService:
    """
    Returns an AttractionService wired with the RapidAPI TripAdvisor scraper client.
    Uses the same RAPIDAPI_KEY as hotels.
    """
    client = TripAdvisorScraperClient(api_key=settings.rapidapi_key)
    return AttractionService(
        destination_provider=client,
        search_provider=client,
        detail_provider=client,
    )


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
    Get full details for a single attraction.

    - `content_id`: Attraction ID from search results (`location_id` field).
    - Returns photos, hours, location, reviews, nearby restaurants/attractions.

    **Flutter flow:**
    1. User taps an attraction from `/attractions/search` results
    2. Call this endpoint with the `location_id` as `content_id`
    3. Render the detail screen with all returned data
    """
    detail = await service.get_attraction_details(
        content_id=content_id,
        start_date=start_date,
        end_date=end_date,
        currency=currency,
        adults=adults,
    )
    return AttractionDetailResponse.from_entity(detail)
