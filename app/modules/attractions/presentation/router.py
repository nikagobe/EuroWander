from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import settings
from app.modules.attractions.application.services import AttractionService
from app.modules.attractions.infrastructure.tripadvisor_client import TripAdvisorClient
from app.modules.attractions.presentation.schemas import (
    AttractionDetailsResponse,
    AttractionLocationResponse,
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


@router.get("/nearby", response_model=list[AttractionLocationResponse])
async def search_nearby(
    latitude: float = Query(..., description="Latitude coordinate (from /cities/search)"),
    longitude: float = Query(..., description="Longitude coordinate (from /cities/search)"),
    category: str = Query("attractions", description="Category: 'attractions' or 'restaurants'"),
    language: str = Query("en", description="Language code"),
    service: AttractionService = Depends(get_attraction_service),
) -> list[AttractionLocationResponse]:
    """
    Find popular attractions or restaurants near a location (e.g. city center).

    **Flutter flow:**
    1. User picks a city from `/cities/search` → gives you `lat` + `lng`.
    2. Call this with those coordinates + category.

    - `latitude` / `longitude`: GPS coordinates.
    - `category`: 'attractions' for landmarks/museums/parks, 'restaurants' for dining/cafés.
    - Results sorted by rating, within 10 km radius.
    """
    locations = await service.search_nearby(
        latitude=latitude,
        longitude=longitude,
        category=category,
        language=language,
    )
    return [AttractionLocationResponse.from_entity(loc) for loc in locations]


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
    - Returns complete info: description, rating, reviews, photos, hours, cuisine (restaurants).
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


