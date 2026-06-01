from abc import ABC, abstractmethod

from app.modules.flights.domain.entities import FlightOffer


class BookingLinkProvider(ABC):
    """
    Abstract interface for resolving a booking_token into a purchasable URL.
    Concrete implementations call SerpApi (booking_token re-search) then
    follow Google's redirect to extract the final vendor link.
    """

    @abstractmethod
    async def fetch_booking_options(
        self,
        booking_token: str,
        departure_id: str,   # IATA or freebase_id
        arrival_id: str,     # IATA or freebase_id
        outbound_date: str,  # YYYY-MM-DD
    ) -> list[dict]: ...

    @abstractmethod
    async def resolve_url(self, url: str, post_data: str) -> str: ...


class FlightSearchProvider(ABC):
    """
    Abstract interface for any flight-data provider.
    Swap implementations (SerpApi, fake, Amadeus…) without touching business logic.
    """

    @abstractmethod
    async def search(
        self,
        origin: str,
        destination: str,
        outbound_date: str,        # YYYY-MM-DD
        return_date: str | None,   # None = one-way
        adults: int,
    ) -> list[FlightOffer]: ...

    @abstractmethod
    async def search_multi_origin(
        self,
        origins: list[str],        # list of freebase_ids, max 5 per call
        destination: str,          # freebase_id
        outbound_date: str,        # YYYY-MM-DD
        return_date: str | None,
        adults: int,
    ) -> list[FlightOffer]:
        """
        Search flights from multiple origin cities to one destination.
        SerpApi supports up to 5 comma-separated departure_ids per request.
        """
        ...

