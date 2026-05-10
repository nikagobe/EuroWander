from abc import ABC, abstractmethod

from app.modules.flights.domain.entities import FlightOffer


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

