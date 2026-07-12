from app.modules.restaurants.domain.entities import PaginatedRestaurants, RestaurantDetail
from app.modules.restaurants.domain.interfaces import (
    RestaurantDetailProvider,
    RestaurantSearchProvider,
)


class RestaurantService:
    """
    Orchestrates restaurant search and detail business logic.
    Depends on abstract providers — never on concrete clients.
    """

    def __init__(
        self,
        search_provider: RestaurantSearchProvider,
        detail_provider: RestaurantDetailProvider | None = None,
    ) -> None:
        self._search_provider = search_provider
        self._detail_provider = detail_provider

    async def search_restaurants(
        self,
        geo_id: int,
        page: int = 1,
        currency: str = "EUR",
        sort: str = "POPULARITY",
        update_token: str | None = None,
        query: str | None = None,
    ) -> PaginatedRestaurants:
        """
        Search for restaurants in a city by geo ID.
        Optional `query` filters results by name/keyword.
        Returns a paginated list — Flutter handles page navigation.
        For page > 1, pass the `update_token` from the previous response.
        """
        return await self._search_provider.search_restaurants(
            geo_id=geo_id,
            page=page,
            currency=currency,
            sort=sort,
            update_token=update_token,
            query=query,
        )

    async def get_restaurant_details(
        self,
        content_id: str,
        currency: str = "EUR",
    ) -> RestaurantDetail:
        """
        Fetch full restaurant details by content ID.
        The content_id comes from the search results
        (cardLink → route → typedParams → contentId).
        """
        if not self._detail_provider:
            raise RuntimeError("Detail provider not configured")
        return await self._detail_provider.get_restaurant_details(
            content_id=content_id,
            currency=currency,
        )
