from abc import ABC, abstractmethod

from app.modules.schedule.domain.entities import ScheduleItem


class ScheduleRepository(ABC):
    """
    Abstract interface for persisting manual schedule items (attractions, restaurants).
    Auto-items are computed on-the-fly from trip data — never persisted here.
    """

    @abstractmethod
    async def get_manual_items(self, trip_id: str) -> list[ScheduleItem]: ...

    @abstractmethod
    async def add_item(self, trip_id: str, item: ScheduleItem) -> ScheduleItem: ...

    @abstractmethod
    async def update_item(
        self,
        trip_id: str,
        item_id: str,
        day_date: str | None = None,
        time_slot: str | None = None,
        title: str | None = None,
        subtitle: str | None = None,
        note: str | None = None,
        order: int | None = None,
    ) -> ScheduleItem | None: ...

    @abstractmethod
    async def remove_item(self, trip_id: str, item_id: str) -> bool: ...

    @abstractmethod
    async def ensure_indexes(self) -> None: ...

