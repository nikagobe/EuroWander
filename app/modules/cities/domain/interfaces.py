from abc import ABC, abstractmethod

from app.modules.cities.domain.entities import City


class CityRepository(ABC):
    """Abstract interface — business logic depends on this, not MongoDB."""

    @abstractmethod
    async def search_by_name(self, query: str, limit: int) -> list[City]: ...

