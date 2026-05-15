from abc import ABC, abstractmethod

from app.modules.airports.domain.entities import Airport


class AirportRepository(ABC):

    @abstractmethod
    async def get_by_iata(self, iata_code: str) -> Airport | None: ...

    @abstractmethod
    async def get_by_country(self, country_code: str) -> list[Airport]: ...

    @abstractmethod
    async def search(self, query: str, limit: int) -> list[Airport]: ...

