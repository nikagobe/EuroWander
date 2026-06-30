from abc import ABC, abstractmethod

from app.modules.attractions.domain.entities import AttractionDetails, AttractionLocation, PaginatedLocations


class AttractionSearchProvider(ABC):
    """
    Abstract interface for searching attractions/restaurants by keyword or coordinates.
    Swap implementations (TripAdvisor, mock) without touching business logic.
    """

    @abstractmethod
    async def search_locations(
        self,
        query: str,
        category: str,
        language: str,
    ) -> list[AttractionLocation]: ...

    @abstractmethod
    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        category: str,
        language: str,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedLocations: ...


class AttractionDetailsProvider(ABC):
    """
    Abstract interface for fetching full details (including photos/reviews)
    for a single attraction or restaurant.
    """

    @abstractmethod
    async def get_location_details(
        self,
        location_id: str,
        language: str,
        currency: str,
    ) -> AttractionDetails | None: ...
