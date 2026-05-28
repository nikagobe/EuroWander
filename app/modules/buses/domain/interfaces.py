from abc import ABC, abstractmethod

from app.modules.buses.domain.entities import BusOffer


class BusSearchProvider(ABC):
    """
    Abstract interface for any bus-ticket provider.
    Swap implementations (Flixbus via RapidAPI, fake…) without touching business logic.
    """

    @abstractmethod
    async def search(
        self,
        from_id: str,       # Flixbus city UUID
        to_id: str,         # Flixbus city UUID
        date: str,          # DD.MM.YYYY  (Flixbus format)
        adults: int,
        currency: str,
    ) -> list[BusOffer]: ...

