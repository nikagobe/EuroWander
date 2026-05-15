from abc import ABC, abstractmethod

from app.modules.countries.domain.entities import Country


class CountryRepository(ABC):
    @abstractmethod
    async def get_by_name(self, name: str) -> Country | None: ...

    @abstractmethod
    async def get_neighbors_with_cities(self, name: str) -> list[Country]: ...

