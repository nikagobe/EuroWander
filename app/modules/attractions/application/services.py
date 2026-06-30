from app.modules.attractions.domain.entities import AttractionDetails, AttractionLocation
from app.modules.attractions.domain.interfaces import (
    AttractionDetailsProvider,
    AttractionSearchProvider,
)


class AttractionService:
    """
    Orchestrates attraction/restaurant business logic.
    Depends on abstract providers — never on concrete clients.
    """

    def __init__(
        self,
        search_provider: AttractionSearchProvider,
        details_provider: AttractionDetailsProvider,
    ) -> None:
        self._search_provider = search_provider
        self._details_provider = details_provider

    async def search_attractions(
        self,
        query: str,
        language: str = "en",
    ) -> list[AttractionLocation]:
        """
        Search for attractions (landmarks, museums, parks, etc.) by keyword.
        Returns empty list for blank queries.
        """
        if not query or not query.strip():
            return []
        return await self._search_provider.search_locations(
            query=query.strip(),
            category="attractions",
            language=language,
        )

    async def search_restaurants(
        self,
        query: str,
        language: str = "en",
    ) -> list[AttractionLocation]:
        """
        Search for restaurants and cafés by keyword.
        Returns empty list for blank queries.
        """
        if not query or not query.strip():
            return []
        return await self._search_provider.search_locations(
            query=query.strip(),
            category="restaurants",
            language=language,
        )

    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        category: str = "attractions",
        language: str = "en",
    ) -> list[AttractionLocation]:
        """
        Search for attractions or restaurants near given coordinates.
        Category must be 'attractions' or 'restaurants'.
        """
        valid_categories = ("attractions", "restaurants")
        if category not in valid_categories:
            category = "attractions"
        return await self._search_provider.search_nearby(
            latitude=latitude,
            longitude=longitude,
            category=category,
            language=language,
        )


    async def get_details(
        self,
        location_id: str,
        language: str = "en",
        currency: str = "EUR",
    ) -> AttractionDetails | None:
        """
        Fetch detailed information for a specific attraction or restaurant.
        Returns None if the location is not found.
        """
        if not location_id or not location_id.strip():
            return None
        return await self._details_provider.get_location_details(
            location_id=location_id.strip(),
            language=language,
            currency=currency,
        )


