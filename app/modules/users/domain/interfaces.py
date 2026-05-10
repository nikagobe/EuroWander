from abc import ABC, abstractmethod

from app.modules.users.domain.entities import User


class UserRepository(ABC):
    """Abstract interface — services depend on this, not on MongoDB."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> User | None: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

