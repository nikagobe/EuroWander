"""
Photo domain interfaces (ABCs).

These contracts decouple application logic from infrastructure concerns.
"""

from abc import ABC, abstractmethod

from app.modules.photos.domain.entities import Photo


class PhotoRepository(ABC):
    """Persistence contract for photo metadata."""

    @abstractmethod
    async def create(self, photo: Photo) -> Photo: ...

    @abstractmethod
    async def list_by_trip(self, trip_id: str) -> list[Photo]: ...

    @abstractmethod
    async def list_by_trip_paginated(
        self, trip_id: str, skip: int, limit: int
    ) -> list[Photo]: ...

    @abstractmethod
    async def get_by_id(self, photo_id: str) -> Photo | None: ...

    @abstractmethod
    async def delete(self, photo_id: str) -> bool: ...

    @abstractmethod
    async def count_by_trip(self, trip_id: str) -> int: ...

