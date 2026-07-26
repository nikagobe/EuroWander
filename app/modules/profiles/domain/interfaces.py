from abc import ABC, abstractmethod

from app.modules.profiles.domain.entities import UserProfile


class ProfileRepository(ABC):
    """Abstract interface for user profile persistence."""

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> UserProfile | None: ...

    @abstractmethod
    async def upsert(self, profile: UserProfile) -> UserProfile: ...

