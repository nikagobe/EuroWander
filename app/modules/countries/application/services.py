from app.modules.countries.domain.entities import Country
from app.modules.countries.domain.interfaces import CountryRepository


class CountryService:
    def __init__(self, repo: CountryRepository) -> None:
        self._repo = repo

    async def get_country(self, name: str) -> Country | None:
        return await self._repo.get_by_name(name)

    async def get_neighbors_with_cities(self, country_name: str) -> list[Country]:
        """
        Return all neighboring countries with their major cities.
        Used for flight suggestion: given a departure country, surface
        the top cities in bordering countries as destination suggestions.
        """
        return await self._repo.get_neighbors_with_cities(country_name)

