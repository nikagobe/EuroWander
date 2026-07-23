from app.modules.attractions.domain.entities import (
    AttractionDestination,
    AttractionDetail,
    PaginatedAttractions,
)
from app.modules.attractions.domain.interfaces import (
    AttractionDestinationProvider,
    AttractionDetailProvider,
    AttractionNameSearchProvider,
    AttractionSearchProvider,
)


class AttractionService:
    """
    Orchestrates attraction business logic.
    Depends on abstract providers — never on concrete clients.
    """

    def __init__(
        self,
        destination_provider: AttractionDestinationProvider,
        search_provider: AttractionSearchProvider,
        detail_provider: AttractionDetailProvider,
        name_search_provider: AttractionNameSearchProvider | None = None,
    ) -> None:
        self._destination_provider = destination_provider
        self._search_provider = search_provider
        self._detail_provider = detail_provider
        self._name_search_provider = name_search_provider

    async def search_destinations(self, query: str) -> list[AttractionDestination]:
        """
        Search for city destinations for attraction browsing.
        Returns empty list for blank queries.
        """
        if not query or not query.strip():
            return []
        return await self._destination_provider.search_destinations(query=query.strip())

    async def search_attractions(
        self,
        geo_id: int,
        start_date: str,
        end_date: str,
        adults: int = 1,
        page: int = 1,
        currency: str = "EUR",
        sort: str = "TRAVELER_FAVORITE_V2",
        query: str | None = None,
    ) -> PaginatedAttractions:
        """
        Search for attractions in a city by geo ID.
        Optional `query` filters results by name/keyword.
        Returns a paginated list — Flutter handles page navigation.
        """
        return await self._search_provider.search_attractions(
            geo_id=geo_id,
            start_date=start_date,
            end_date=end_date,
            adults=adults,
            page=page,
            currency=currency,
            sort=sort,
            query=query,
        )

    async def get_attraction_details(
        self,
        content_id: str,
        start_date: str,
        end_date: str,
        currency: str = "EUR",
        adults: int = 1,
    ) -> AttractionDetail:
        """
        Get full details of an attraction by content ID.
        Returns photos, hours, location, reviews, and nearby places.
        """
        return await self._detail_provider.get_attraction_details(
            content_id=content_id,
            start_date=start_date,
            end_date=end_date,
            currency=currency,
            adults=adults,
        )

    async def search_by_name(
        self,
        query: str,
        category: str | None = None,
        geo_name: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedAttractions:
        """
        Search attractions/restaurants by free-text name (Terra API).
        Does NOT require a geo_id — works globally or scoped by city name.
        """
        if not self._name_search_provider:
            raise RuntimeError("Name search provider not configured")
        if not query or not query.strip():
            return PaginatedAttractions(items=[], current_page=1, total_pages=0, total_results=0, page_size=size)
        return await self._name_search_provider.search_by_name(
            query=query.strip(),
            category=category,
            geo_name=geo_name,
            page=page,
            size=size,
        )
