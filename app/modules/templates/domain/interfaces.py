"""Template repository interface (ABC)."""

from abc import ABC, abstractmethod

from app.modules.templates.domain.entities import TripTemplate


class TemplateRepository(ABC):
    @abstractmethod
    async def create(self, template: TripTemplate) -> TripTemplate: ...

    @abstractmethod
    async def get_by_id(self, template_id: str) -> TripTemplate | None: ...

    @abstractmethod
    async def update(self, template: TripTemplate) -> TripTemplate: ...

    @abstractmethod
    async def delete(self, template_id: str) -> bool: ...

    @abstractmethod
    async def list_published(
        self,
        skip: int = 0,
        limit: int = 20,
        tags: list[str] | None = None,
        destination: str | None = None,
        sort_by: str = "newest",
    ) -> list[TripTemplate]: ...

    @abstractmethod
    async def list_by_author(self, author_id: str, skip: int = 0, limit: int = 20) -> list[TripTemplate]: ...

    @abstractmethod
    async def increment_fork_count(self, template_id: str) -> None: ...

    @abstractmethod
    async def ensure_indexes(self) -> None: ...

