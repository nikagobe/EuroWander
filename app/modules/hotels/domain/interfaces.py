from abc import ABC, abstractmethod

from app.modules.hotels.domain.entities import HotelDestination, HotelDetails, HotelOffer


class HotelDestinationProvider(ABC):
    """
    Abstract interface for searching hotel destinations (autocomplete).
    Swap implementations (Booking.com via RapidAPI, fake/mock…) without touching business logic.
    """

    @abstractmethod
    async def search_destinations(self, query: str) -> list[HotelDestination]: ...


class HotelSearchProvider(ABC):
    """
    Abstract interface for searching hotels by destination.
    Swap implementations (Booking.com via RapidAPI, fake…) without touching business logic.
    """

    @abstractmethod
    async def search_hotels(
        self,
        dest_id: str,
        search_type: str,
        arrival_date: str,
        departure_date: str,
        adults: int,
        room_qty: int,
        page_number: int,
        currency_code: str,
        sort_by: str,
        price_min: int | None,
        price_max: int | None,
    ) -> list[HotelOffer]: ...


class HotelDetailsProvider(ABC):
    """
    Abstract interface for fetching single hotel details.
    """

    @abstractmethod
    async def get_hotel_details(
        self,
        hotel_id: int,
        arrival_date: str,
        departure_date: str,
        adults: int,
        room_qty: int,
        currency_code: str,
    ) -> HotelDetails | None: ...


