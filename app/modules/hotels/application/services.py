from app.modules.hotels.domain.entities import HotelDestination, HotelDetails, HotelOffer
from app.modules.hotels.domain.interfaces import (
    HotelDestinationProvider,
    HotelDetailsProvider,
    HotelSearchProvider,
)


class HotelService:
    """
    Orchestrates hotel-related business logic.
    Depends on abstract providers — never on concrete clients.
    """

    def __init__(
        self,
        destination_provider: HotelDestinationProvider,
        search_provider: HotelSearchProvider,
        details_provider: HotelDetailsProvider,
    ) -> None:
        self._destination_provider = destination_provider
        self._search_provider = search_provider
        self._details_provider = details_provider

    # ...existing code...

    async def get_hotel_details(
        self,
        hotel_id: int,
        arrival_date: str,
        departure_date: str,
        adults: int = 1,
        room_qty: int = 1,
        currency_code: str = "EUR",
    ) -> HotelDetails | None:
        """
        Fetch detailed information for a single hotel.
        Returns None if the hotel is not found.
        """
        return await self._details_provider.get_hotel_details(
            hotel_id=hotel_id,
            arrival_date=arrival_date,
            departure_date=departure_date,
            adults=adults,
            room_qty=room_qty,
            currency_code=currency_code,
        )

    async def search_destinations(self, query: str) -> list[HotelDestination]:
        """
        Search for hotel destinations by query string.
        Returns matching destinations from Booking.com's autocomplete.
        """
        if not query or not query.strip():
            return []

        return await self._destination_provider.search_destinations(query.strip())

    async def search_hotels(
        self,
        dest_id: str,
        search_type: str,
        arrival_date: str,
        departure_date: str,
        adults: int = 1,
        room_qty: int = 1,
        page_number: int = 1,
        currency_code: str = "EUR",
        sort_by: str = "price",
        price_min: int | None = None,
        price_max: int | None = None,
    ) -> list[HotelOffer]:
        """
        Search hotels for a given destination and date range.
        Returns a list of hotel offers sorted by the specified criterion.
        """
        return await self._search_provider.search_hotels(
            dest_id=dest_id,
            search_type=search_type,
            arrival_date=arrival_date,
            departure_date=departure_date,
            adults=adults,
            room_qty=room_qty,
            page_number=page_number,
            currency_code=currency_code,
            sort_by=sort_by,
            price_min=price_min,
            price_max=price_max,
        )

    async def search_hotels_by_name(
        self,
        query: str,
        arrival_date: str,
        departure_date: str,
        adults: int = 1,
        room_qty: int = 1,
        currency_code: str = "EUR",
    ) -> list[HotelDetails]:
        """
        Search hotels by name using Booking.com's autocomplete, then fetch
        details (with pricing) for each hotel result.
        This is reliable because autocomplete natively searches by hotel name.
        """
        if not query or not query.strip():
            return []

        destinations = await self._destination_provider.search_destinations(query.strip())

        # Filter to hotel-type results only
        hotel_dests = [d for d in destinations if d.search_type == "hotel" and d.hotel_id]

        # Fetch details (with pricing) for each hotel
        results: list[HotelDetails] = []
        for dest in hotel_dests:
            detail = await self._details_provider.get_hotel_details(
                hotel_id=dest.hotel_id,
                arrival_date=arrival_date,
                departure_date=departure_date,
                adults=adults,
                room_qty=room_qty,
                currency_code=currency_code,
            )
            if detail is not None:
                results.append(detail)

        return results

