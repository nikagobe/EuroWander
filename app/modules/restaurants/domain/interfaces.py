from abc import ABC, abstractmethod

from app.modules.restaurants.domain.entities import PaginatedRestaurants, RestaurantDetail


class RestaurantSearchProvider(ABC):
    """
    Abstract interface for searching restaurants by geo ID.
    Swap implementations (RapidAPI TripAdvisor scraper, mock) without touching business logic.
    """

    @abstractmethod
    async def search_restaurants(
        self,
        geo_id: int,
        page: int,
        currency: str,
        sort: str,
        update_token: str | None,
    ) -> PaginatedRestaurants: ...


class RestaurantDetailProvider(ABC):
    """
    Abstract interface for fetching restaurant details by content ID.
    Decouples business logic from the external TripAdvisor API.
    """

    @abstractmethod
    async def get_restaurant_details(
        self,
        content_id: str,
        currency: str,
    ) -> RestaurantDetail: ...
