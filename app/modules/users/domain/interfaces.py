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

    @abstractmethod
    async def search(self, query: str, exclude_user_id: str, limit: int) -> list[User]:
        """Case-insensitive partial match on first_name, last_name, or email.
        Excludes the requesting user from results."""
        ...

