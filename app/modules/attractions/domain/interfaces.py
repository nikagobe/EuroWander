from abc import ABC, abstractmethod

from app.modules.attractions.domain.entities import (
    AttractionDestination,
    AttractionDetail,
    PaginatedAttractions,
)


class AttractionDestinationProvider(ABC):
    """
    Abstract interface for searching attraction destinations (autocomplete).
    Swap implementations (RapidAPI TripAdvisor scraper, mock) without touching business logic.
    """

    @abstractmethod
    async def search_destinations(self, query: str) -> list[AttractionDestination]: ...


class AttractionSearchProvider(ABC):
    """
    Abstract interface for searching attractions by geo ID.
    """

    @abstractmethod
    async def search_attractions(
        self,
        geo_id: int,
        start_date: str,
        end_date: str,
        adults: int,
        page: int,
        currency: str,
        sort: str,
    ) -> PaginatedAttractions: ...


class AttractionDetailProvider(ABC):
    """
    Abstract interface for fetching attraction details by content ID.
    Decouples business logic from the external TripAdvisor API.
    """

    @abstractmethod
    async def get_attraction_details(
        self,
        content_id: str,
        start_date: str,
        end_date: str,
        currency: str,
        adults: int,
    ) -> AttractionDetail: ...
