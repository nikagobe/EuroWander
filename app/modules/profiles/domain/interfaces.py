from abc import ABC, abstractmethod
from datetime import datetime

from app.modules.profiles.domain.entities import UserProfile


class ProfileRepository(ABC):
    """Abstract interface for user profile persistence."""

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> UserProfile | None: ...

    @abstractmethod
    async def upsert(self, profile: UserProfile) -> UserProfile: ...


class ProfileStorageProvider(ABC):
    """Contract for generating presigned URLs for profile photo uploads."""

    @abstractmethod
    async def generate_upload_url(
        self, file_key: str, content_type: str, size_bytes: int
    ) -> tuple[str, datetime]:
        """Return (presigned_put_url, expires_at)."""
        ...

    @abstractmethod
    async def generate_download_url(self, file_key: str) -> tuple[str, datetime]:
        """Return (presigned_get_url, expires_at)."""
        ...

    @abstractmethod
    async def delete_file(self, file_key: str) -> None: ...
