from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.config import settings
from app.modules.hotels.application.services import HotelService
from app.modules.hotels.infrastructure.booking_client import BookingComClient
from app.modules.hotels.infrastructure.fake_client import FakeBookingClient
from app.modules.hotels.presentation.schemas import (
    HotelDestinationResponse,
    HotelDetailsResponse,
    HotelOfferResponse,
    HotelSearchRequest,
)

router = APIRouter(prefix="/hotels", tags=["hotels"])


def get_hotel_service() -> HotelService:
    """
    Returns a HotelService wired with real Booking.com client when RAPIDAPI_KEY
    is configured, or the fake client otherwise.
    """
    if settings.rapidapi_key:
        client = BookingComClient(api_key=settings.rapidapi_key)
    else:
        client = FakeBookingClient()
    # Client implements all three provider interfaces
    return HotelService(
        destination_provider=client,
        search_provider=client,
        details_provider=client,
    )


@router.get("/destinations", response_model=list[HotelDestinationResponse])
async def search_destinations(
    query: str = Query(..., min_length=2, description="Destination search query (e.g. 'Paris')"),
    service: HotelService = Depends(get_hotel_service),
) -> list[HotelDestinationResponse]:
    """
    Search for hotel destinations using Booking.com's autocomplete.

    - `query`: Free-text search (city, district, region…). Minimum 2 characters.
    - Returns a list of matching destinations with their Booking.com `dest_id`,
      which is required for subsequent hotel search requests.
    """
    destinations = await service.search_destinations(query)
    return [HotelDestinationResponse.from_entity(d) for d in destinations]


@router.post("/search", response_model=list[HotelOfferResponse])
async def search_hotels(
    req: HotelSearchRequest,
    service: HotelService = Depends(get_hotel_service),
) -> list[HotelOfferResponse]:
    """
    Search for hotels in a destination.

    - `dest_id`: Booking.com destination ID (from `/hotels/destinations`).
    - `search_type`: Usually "CITY" or "DISTRICT".
    - `arrival_date` / `departure_date`: YYYY-MM-DD format.
    - `sort_by`: "price", "review_score", "popularity", etc.
    - Optional `price_min` / `price_max` to filter by nightly rate.

    Returns hotel offers with name, coordinates, price, rating, and photo.
    """
    hotels = await service.search_hotels(
        dest_id=req.dest_id,
        search_type=req.search_type,
        arrival_date=req.arrival_date,
        departure_date=req.departure_date,
        adults=req.adults,
        room_qty=req.room_qty,
        page_number=req.page_number,
        currency_code=req.currency_code,
        sort_by=req.sort_by,
        price_min=req.price_min,
        price_max=req.price_max,
    )
    return [HotelOfferResponse.from_entity(h) for h in hotels]


@router.get("/search-by-name", response_model=list[HotelDetailsResponse])
async def search_hotels_by_name(
    query: str = Query(..., min_length=2, description="Hotel name search (e.g. 'Hotel Arts', 'Hilton')"),
    arrival_date: str = Query(..., description="Check-in date (YYYY-MM-DD)"),
    departure_date: str = Query(..., description="Check-out date (YYYY-MM-DD)"),
    adults: int = Query(1, ge=1, description="Number of adults"),
    room_qty: int = Query(1, ge=1, description="Number of rooms"),
    currency_code: str = Query("EUR", description="Currency code"),
    service: HotelService = Depends(get_hotel_service),
) -> list[HotelDetailsResponse]:
    """
    Search hotels by name using Booking.com autocomplete.

    - `query`: Hotel name (min 2 chars). Booking.com searches natively by name.
    - Returns full hotel details with pricing for matching hotels.
    - Use this for the search bar on the hotel browsing page.

    **Flutter flow:**
    1. User types hotel name in search bar (debounced)
    2. Call this endpoint with the text + dates
    3. Show results with full details and pricing
    """
    results = await service.search_hotels_by_name(
        query=query,
        arrival_date=arrival_date,
        departure_date=departure_date,
        adults=adults,
        room_qty=room_qty,
        currency_code=currency_code,
    )
    return [HotelDetailsResponse.from_entity(h) for h in results]


@router.get("/details/{hotel_id}", response_model=HotelDetailsResponse)
async def get_hotel_details(
    hotel_id: int,
    arrival_date: str = Query(..., description="Check-in date (YYYY-MM-DD)"),
    departure_date: str = Query(..., description="Check-out date (YYYY-MM-DD)"),
    adults: int = Query(1, ge=1, description="Number of adults"),
    room_qty: int = Query(1, ge=1, description="Number of rooms"),
    currency_code: str = Query("EUR", description="Currency code (e.g. EUR, USD)"),
    service: HotelService = Depends(get_hotel_service),
) -> HotelDetailsResponse:
    """
    Get detailed information for a single hotel.

    - `hotel_id`: Booking.com hotel ID (from `/hotels/search` results).
    - `arrival_date` / `departure_date`: YYYY-MM-DD format.
    - Returns full details including photos, facilities, room info, and pricing.
    """
    details = await service.get_hotel_details(
        hotel_id=hotel_id,
        arrival_date=arrival_date,
        departure_date=departure_date,
        adults=adults,
        room_qty=room_qty,
        currency_code=currency_code,
    )
    if details is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hotel with id {hotel_id} not found.",
        )
    return HotelDetailsResponse.from_entity(details)
