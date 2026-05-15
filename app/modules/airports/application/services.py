from app.modules.airports.domain.entities import Airport
from app.modules.airports.domain.interfaces import AirportRepository


class AirportService:

    def __init__(self, repo: AirportRepository) -> None:
        self._repo = repo

    async def get_by_iata(self, iata_code: str) -> Airport | None:
        return await self._repo.get_by_iata(iata_code)

    async def get_by_country(self, country_code: str) -> list[Airport]:
        return await self._repo.get_by_country(country_code)

    async def search(self, query: str, limit: int = 10) -> list[Airport]:
        return await self._repo.search(query.strip(), limit)

