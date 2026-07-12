"""
Playlist application service.

Orchestrates playlist CRUD, search, like/unlike, fork, import-to-schedule,
and review management.  Business logic lives here — never in routers or repos.
"""

from datetime import datetime

from app.modules.playlists.domain.entities import (
    BudgetTier,
    Playlist,
    PlaylistItem,
    PlaylistItemType,
    PlaylistReview,
    PlaylistTimeSlot,
    PlaylistVibe,
)
from app.modules.playlists.domain.interfaces import (
    PlaylistRepository,
    PlaylistReviewRepository,
)
from app.modules.schedule.domain.entities import ScheduleItem, ScheduleItemType, TimeSlot
from app.modules.schedule.domain.interfaces import ScheduleRepository
from app.modules.trips.domain.interfaces import TripRepository


class PlaylistService:
    """Orchestrates playlist logic — never touches DB directly."""

    def __init__(
        self,
        playlist_repo: PlaylistRepository,
        review_repo: PlaylistReviewRepository,
        schedule_repo: ScheduleRepository | None = None,
        trip_repo: TripRepository | None = None,
    ) -> None:
        self._playlist_repo = playlist_repo
        self._review_repo = review_repo
        self._schedule_repo = schedule_repo
        self._trip_repo = trip_repo

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def create_playlist(
        self,
        creator_id: str,
        city: str,
        country: str,
        title: str,
        description: str = "",
        cover_photo_url: str = "",
        vibe: str | list[str] = "chill",
        budget_tier: str = "mid_range",
        tags: list[str] | None = None,
        total_days: int = 1,
        is_public: bool = True,
        items: list[dict] | None = None,
    ) -> Playlist:
        """Create a new playlist."""
        playlist = Playlist(
            creator_id=creator_id,
            city=city,
            country=country,
            title=title,
            description=description,
            cover_photo_url=cover_photo_url,
            vibe=_parse_vibes(vibe),
            budget_tier=BudgetTier(budget_tier),
            tags=tags or [],
            total_days=total_days,
            is_public=is_public,
            items=[_dict_to_playlist_item(i) for i in (items or [])],
        )
        return await self._playlist_repo.create(playlist)

    async def get_playlist(self, playlist_id: str) -> Playlist:
        """Get a playlist by ID."""
        playlist = await self._playlist_repo.get_by_id(playlist_id)
        if not playlist:
            raise ValueError("Playlist not found")
        return playlist

    async def update_playlist(
        self,
        playlist_id: str,
        user_id: str,
        **updates: object,
    ) -> Playlist:
        """Update a playlist — only the owner can update."""
        playlist = await self._playlist_repo.get_by_id(playlist_id)
        if not playlist:
            raise ValueError("Playlist not found")
        if not playlist.is_owner(user_id):
            raise PermissionError("Only the playlist owner can edit")

        # Apply scalar fields
        for key in ("title", "description", "cover_photo_url", "city", "country",
                     "total_days", "is_public"):
            if key in updates and updates[key] is not None:
                setattr(playlist, key, updates[key])

        if "vibe" in updates and updates["vibe"] is not None:
            playlist.vibe = _parse_vibes(updates["vibe"])
        if "budget_tier" in updates and updates["budget_tier"] is not None:
            playlist.budget_tier = BudgetTier(str(updates["budget_tier"]))
        if "tags" in updates and updates["tags"] is not None:
            playlist.tags = list(updates["tags"])  # type: ignore[arg-type]
        if "items" in updates and updates["items"] is not None:
            playlist.items = [_dict_to_playlist_item(i) for i in updates["items"]]  # type: ignore[union-attr]

        playlist.updated_at = datetime.utcnow()
        result = await self._playlist_repo.update(playlist)
        if not result:
            raise ValueError("Failed to update playlist")
        return result

    async def delete_playlist(self, playlist_id: str, user_id: str) -> None:
        """Delete a playlist — only the owner can delete."""
        playlist = await self._playlist_repo.get_by_id(playlist_id)
        if not playlist:
            raise ValueError("Playlist not found")
        if not playlist.is_owner(user_id):
            raise PermissionError("Only the playlist owner can delete")
        await self._playlist_repo.delete(playlist_id)

    # ── Search & Discovery ───────────────────────────────────────────────────

    async def search_playlists(
        self,
        city: str | None = None,
        country: str | None = None,
        vibe: str | None = None,
        budget_tier: str | None = None,
        keyword: str | None = None,
        sort_by: str = "popular",
        skip: int = 0,
        limit: int = 20,
    ) -> list[Playlist]:
        """Search public playlists with filters."""
        return await self._playlist_repo.search(
            city=city, country=country, vibe=vibe,
            budget_tier=budget_tier, keyword=keyword,
            sort_by=sort_by, skip=skip, limit=limit,
        )

    async def get_user_playlists(self, user_id: str) -> list[Playlist]:
        """Get all playlists created by a user."""
        return await self._playlist_repo.get_by_creator(user_id)

    async def list_cities(self) -> list[str]:
        """List cities that have at least one public playlist."""
        return await self._playlist_repo.list_cities_with_playlists()

    # ── Like / Unlike ────────────────────────────────────────────────────────

    async def toggle_like(self, playlist_id: str, user_id: str) -> bool:
        """Toggle like. Returns True if now liked, False if unliked."""
        playlist = await self._playlist_repo.get_by_id(playlist_id)
        if not playlist:
            raise ValueError("Playlist not found")
        liked = playlist.toggle_like(user_id)
        await self._playlist_repo.update(playlist)
        return liked

    # ── Fork ─────────────────────────────────────────────────────────────────

    async def fork_playlist(self, playlist_id: str, user_id: str) -> Playlist:
        """Copy a playlist to the user's own collection."""
        original = await self._playlist_repo.get_by_id(playlist_id)
        if not original:
            raise ValueError("Playlist not found")

        forked = Playlist(
            creator_id=user_id,
            city=original.city,
            country=original.country,
            title=f"{original.title} (copy)",
            description=original.description,
            cover_photo_url=original.cover_photo_url,
            vibe=original.vibe,
            budget_tier=original.budget_tier,
            items=list(original.items),
            tags=list(original.tags),
            total_days=original.total_days,
            is_public=False,  # Forked copies start private
        )
        return await self._playlist_repo.create(forked)

    # ── Import to Trip Schedule ──────────────────────────────────────────────

    async def import_to_schedule(
        self,
        playlist_id: str,
        trip_id: str,
        user_id: str,
        start_date: str,
    ) -> int:
        """
        Import playlist items into a trip schedule.

        Maps playlist day_number offsets onto real dates starting from start_date.
        If the playlist has more days than the trip, overflow items are still
        created as schedule items — they won't appear in the day-based view but
        will be returned in the "unscheduled" list so the user can rearrange them.

        Returns the number of schedule items created.
        """
        if not self._schedule_repo or not self._trip_repo:
            raise RuntimeError("Schedule/Trip repos not configured for import")

        playlist = await self._playlist_repo.get_by_id(playlist_id)
        if not playlist:
            raise ValueError("Playlist not found")

        trip = await self._trip_repo.get_by_id(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found or access denied")

        from datetime import date, timedelta
        base = date.fromisoformat(start_date)
        count = 0

        for item in playlist.items:
            real_date = base + timedelta(days=item.day_number - 1)
            schedule_item = ScheduleItem(
                day_date=real_date.isoformat(),
                time_slot=TimeSlot(item.time_slot.value),
                item_type=_playlist_type_to_schedule_type(item.item_type),
                title=item.name,
                subtitle=item.category or item.address,
                reference_id=item.location_id,
                note=item.note,
                is_auto=False,
            )
            await self._schedule_repo.add_item(trip_id, schedule_item)
            count += 1

        # Track import count
        await self._playlist_repo.increment_import_count(playlist_id)
        return count

    # ── Reviews ──────────────────────────────────────────────────────────────

    async def add_review(
        self,
        playlist_id: str,
        user_id: str,
        user_first_name: str,
        user_last_name: str,
        rating: int,
        comment: str = "",
    ) -> PlaylistReview:
        """Add a review to a playlist and update cached stats."""
        # Validate playlist exists
        playlist = await self._playlist_repo.get_by_id(playlist_id)
        if not playlist:
            raise ValueError("Playlist not found")
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")

        review = PlaylistReview(
            playlist_id=playlist_id,
            user_id=user_id,
            user_first_name=user_first_name,
            user_last_name=user_last_name,
            rating=rating,
            comment=comment,
        )
        created = await self._review_repo.create(review)

        # Update cached stats on the playlist
        avg, cnt = await self._review_repo.get_stats(playlist_id)
        playlist.update_review_stats(avg, cnt)
        await self._playlist_repo.update(playlist)

        return created

    async def get_reviews(
        self, playlist_id: str, skip: int = 0, limit: int = 20
    ) -> list[PlaylistReview]:
        """Get paginated reviews for a playlist."""
        return await self._review_repo.get_by_playlist(playlist_id, skip=skip, limit=limit)

    async def delete_review(
        self, playlist_id: str, review_id: str, user_id: str
    ) -> None:
        """Delete a review — only the review author can delete."""
        removed = await self._review_repo.delete(review_id, user_id)
        if not removed:
            raise ValueError("Review not found or not your review")
        # Update cached stats
        playlist = await self._playlist_repo.get_by_id(playlist_id)
        if playlist:
            avg, cnt = await self._review_repo.get_stats(playlist_id)
            playlist.update_review_stats(avg, cnt)
            await self._playlist_repo.update(playlist)


# ── Helpers ──────────────────────────────────────────────────────────────────────


def _parse_vibes(raw: str | list[str]) -> list[PlaylistVibe]:
    """Parse vibe input — accepts a single string, comma-separated string, or list."""
    if isinstance(raw, list):
        return [PlaylistVibe(v.strip()) for v in raw if v.strip()]
    return [PlaylistVibe(v.strip()) for v in raw.split(",") if v.strip()]


def _dict_to_playlist_item(d: dict) -> PlaylistItem:
    """Convert a dict (from request body) to a PlaylistItem."""
    return PlaylistItem(
        item_type=PlaylistItemType(d.get("item_type", "attraction")),
        name=d["name"],
        day_number=d.get("day_number", 1),
        time_slot=PlaylistTimeSlot(d.get("time_slot", "morning")),
        order=d.get("order", 0),
        location_id=d.get("location_id", ""),
        category=d.get("category", ""),
        photo_url=d.get("photo_url", ""),
        latitude=d.get("latitude", 0.0),
        longitude=d.get("longitude", 0.0),
        address=d.get("address", ""),
        rating=d.get("rating", 0.0),
        num_reviews=d.get("num_reviews", 0),
        price_indicator=d.get("price_indicator", ""),
        note=d.get("note", ""),
        suggested_duration_minutes=d.get("suggested_duration_minutes", 60),
    )


def _playlist_type_to_schedule_type(pt: PlaylistItemType) -> ScheduleItemType:
    """Map playlist item type to schedule item type."""
    mapping = {
        PlaylistItemType.ATTRACTION: ScheduleItemType.ATTRACTION,
        PlaylistItemType.RESTAURANT: ScheduleItemType.RESTAURANT,
        PlaylistItemType.CUSTOM: ScheduleItemType.CUSTOM,
    }
    return mapping.get(pt, ScheduleItemType.ATTRACTION)


