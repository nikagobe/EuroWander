from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import settings
from app.modules.attractions.application.services import AttractionService
from app.modules.attractions.infrastructure.tripadvisor_client import TripAdvisorClient
from app.modules.attractions.presentation.schemas import (
    AttractionDetailsResponse,
    AttractionLocationResponse,
    PaginatedAttractionResponse,
    PaginationMeta,
)

router = APIRouter(prefix="/attractions", tags=["attractions"])


def get_attraction_service() -> AttractionService:
    """
    Returns an AttractionService wired with the TripAdvisor client.
    Requires TRIPADVISOR_KEY in environment.
    """
    client = TripAdvisorClient(api_key=settings.tripadvisor_key)
    return AttractionService(
        search_provider=client,
        details_provider=client,
    )


@router.get("/search", response_model=list[AttractionLocationResponse])
async def search_attractions(
    query: str = Query(..., min_length=2, description="Search keyword (e.g. 'Eiffel Tower', 'Paris museums')"),
    language: str = Query("en", description="Language code (e.g. 'en', 'fr', 'de')"),
    service: AttractionService = Depends(get_attraction_service),
) -> list[AttractionLocationResponse]:
    """
    Search for attractions (landmarks, museums, parks, etc.) by keyword.

    - `query`: Free-text search. Minimum 2 characters.
    - Returns a list of matching attractions with their TripAdvisor `location_id`.
    """
    locations = await service.search_attractions(query=query, language=language)
    return [AttractionLocationResponse.from_entity(loc) for loc in locations]


@router.get("/restaurants/search", response_model=list[AttractionLocationResponse])
async def search_restaurants(
    query: str = Query(..., min_length=2, description="Search keyword (e.g. 'pizza Paris', 'sushi Berlin')"),
    language: str = Query("en", description="Language code (e.g. 'en', 'fr', 'de')"),
    service: AttractionService = Depends(get_attraction_service),
) -> list[AttractionLocationResponse]:
    """
    Search for restaurants and cafés by keyword.

    - `query`: Free-text search. Minimum 2 characters.
    - Returns a list of matching restaurants with their TripAdvisor `location_id`.
    """
    locations = await service.search_restaurants(query=query, language=language)
    return [AttractionLocationResponse.from_entity(loc) for loc in locations]


@router.get("/must-see", response_model=PaginatedAttractionResponse)
async def get_must_see_attractions(
    latitude: float = Query(..., description="City latitude (from /cities/search)"),
    longitude: float = Query(..., description="City longitude (from /cities/search)"),
    language: str = Query("en", description="Language code"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=20, description="Results per page (max 20)"),
    service: AttractionService = Depends(get_attraction_service),
) -> PaginatedAttractionResponse:
    """
    Must-see attractions in a city — top-rated landmarks, museums, and sights.

    **Flutter flow:** User picks a city (gets lat/lng) → call this → show "Must See" section.
    Paginated — use `page` param for infinite scroll.
    """
    result = await service.search_nearby(
        latitude=latitude, longitude=longitude,
        category="attractions", language=language,
        page=page, size=size,
    )
    return PaginatedAttractionResponse(
        data=[AttractionLocationResponse.from_entity(loc) for loc in result.items],
        pagination=PaginationMeta(
            page=result.page, size=result.size,
            total_elements=result.total_elements, total_pages=result.total_pages,
        ),
    )


@router.get("/going-out", response_model=PaginatedAttractionResponse)
async def get_going_out_recommendations(
    latitude: float = Query(..., description="City latitude (from /cities/search)"),
    longitude: float = Query(..., description="City longitude (from /cities/search)"),
    language: str = Query("en", description="Language code"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=20, description="Results per page (max 20)"),
    service: AttractionService = Depends(get_attraction_service),
) -> PaginatedAttractionResponse:
    """
    Popular restaurants, cafés, and bars — top-rated places to eat, drink, and have fun.

    **Flutter flow:** User picks a city (gets lat/lng) → call this → show "Eat, Drink & Nightlife" section.
    Paginated — use `page` param for infinite scroll.
    """
    result = await service.search_nearby(
        latitude=latitude, longitude=longitude,
        category="restaurants", language=language,
        page=page, size=size,
    )
    return PaginatedAttractionResponse(
        data=[AttractionLocationResponse.from_entity(loc) for loc in result.items],
        pagination=PaginationMeta(
            page=result.page, size=result.size,
            total_elements=result.total_elements, total_pages=result.total_pages,
        ),
    )


@router.get("/nearby", response_model=PaginatedAttractionResponse)
async def search_nearby(
    latitude: float = Query(..., description="Latitude coordinate"),
    longitude: float = Query(..., description="Longitude coordinate"),
    category: str = Query("attractions", description="Category: 'attractions' or 'restaurants'"),
    language: str = Query("en", description="Language code"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    size: int = Query(20, ge=1, le=20, description="Results per page (max 20)"),
    service: AttractionService = Depends(get_attraction_service),
) -> PaginatedAttractionResponse:
    """
    Find attractions or restaurants near a location — paginated.

    - `page` / `size`: Pagination controls. Max 20 per page.
    - Results sorted by rating, within 8 km radius.
    """
    result = await service.search_nearby(
        latitude=latitude, longitude=longitude,
        category=category, language=language,
        page=page, size=size,
    )
    return PaginatedAttractionResponse(
        data=[AttractionLocationResponse.from_entity(loc) for loc in result.items],
        pagination=PaginationMeta(
            page=result.page, size=result.size,
            total_elements=result.total_elements, total_pages=result.total_pages,
        ),
    )


@router.get("/details/{location_id}", response_model=AttractionDetailsResponse)
async def get_attraction_details(
    location_id: str,
    language: str = Query("en", description="Language code"),
    currency: str = Query("EUR", description="Currency code (e.g. EUR, USD, GBP)"),
    service: AttractionService = Depends(get_attraction_service),
) -> AttractionDetailsResponse:
    """
    Get full details for a single attraction or restaurant.

    - `location_id`: TripAdvisor location ID (from search results).
    - Returns complete info: description, rating, reviews, photos, hours, cuisine.
    """
    details = await service.get_details(
        location_id=location_id,
        language=language,
        currency=currency,
    )
    if details is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location with id '{location_id}' not found.",
        )
    return AttractionDetailsResponse.from_entity(details)
