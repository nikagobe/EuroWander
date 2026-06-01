from abc import ABC, abstractmethod

from app.modules.countries.domain.entities import Country, MajorCity


class CountryRepository(ABC):
    @abstractmethod
    async def get_by_name(self, name: str) -> Country | None: ...

    @abstractmethod
    async def get_neighbors_with_cities(self, name: str) -> list[Country]: ...

    @abstractmethod
    async def get_city_by_iata(self, iata_code: str) -> MajorCity | None:
        """
        Return the MajorCity whose `airports` list contains the given IATA code.
        Returns None if no major city is matched.
        """
        ...

