from app.modules.cities.domain.entities import City
from app.modules.cities.domain.interfaces import CityRepository

MAX_LIMIT = 20


class CityService:
    def __init__(self, repo: CityRepository) -> None:
        self.repo = repo

    async def search(self, query: str, limit: int = 10) -> list[City]:
        """Search cities by name. Caps results at MAX_LIMIT."""
        capped_limit = min(limit, MAX_LIMIT)
        return await self.repo.search_by_name(query.strip(), capped_limit)

