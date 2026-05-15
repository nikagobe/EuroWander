from abc import ABC, abstractmethod

from app.modules.trips.domain.entities import Trip


class TripRepository(ABC):
    @abstractmethod
    async def create(self, trip: Trip) -> Trip: ...

    @abstractmethod
    async def get_by_id(self, trip_id: str, user_id: str) -> Trip | None: ...

    @abstractmethod
    async def list_by_user(self, user_id: str) -> list[Trip]: ...

    @abstractmethod
    async def delete(self, trip_id: str, user_id: str) -> bool: ...

