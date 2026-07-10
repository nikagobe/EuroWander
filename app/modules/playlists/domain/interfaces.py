"""Abstract interfaces for the Playlist module."""

from abc import ABC, abstractmethod

from app.modules.playlists.domain.entities import Playlist, PlaylistReview


class PlaylistRepository(ABC):
    """Persistence interface for Playlist aggregates."""

    @abstractmethod
    async def create(self, playlist: Playlist) -> Playlist: ...

    @abstractmethod
    async def get_by_id(self, playlist_id: str) -> Playlist | None: ...

    @abstractmethod
    async def update(self, playlist: Playlist) -> Playlist | None: ...

    @abstractmethod
    async def delete(self, playlist_id: str) -> bool: ...

    @abstractmethod
    async def search(
        self,
        *,
        city: str | None = None,
        country: str | None = None,
        vibe: str | None = None,
        budget_tier: str | None = None,
        keyword: str | None = None,
        sort_by: str = "popular",
        skip: int = 0,
        limit: int = 20,
    ) -> list[Playlist]: ...

    @abstractmethod
    async def get_by_creator(self, creator_id: str) -> list[Playlist]: ...

    @abstractmethod
    async def list_cities_with_playlists(self) -> list[str]: ...

    @abstractmethod
    async def increment_import_count(self, playlist_id: str) -> None: ...

    @abstractmethod
    async def ensure_indexes(self) -> None: ...


class PlaylistReviewRepository(ABC):
    """Persistence interface for playlist reviews."""

    @abstractmethod
    async def create(self, review: PlaylistReview) -> PlaylistReview: ...

    @abstractmethod
    async def get_by_playlist(
        self, playlist_id: str, skip: int = 0, limit: int = 20
    ) -> list[PlaylistReview]: ...

    @abstractmethod
    async def delete(self, review_id: str, user_id: str) -> bool: ...

    @abstractmethod
    async def get_stats(self, playlist_id: str) -> tuple[float, int]:
        """Return (average_rating, review_count) for a playlist."""
        ...

    @abstractmethod
    async def ensure_indexes(self) -> None: ...

