"""MongoDB repositories for playlists and reviews."""

import logging
from datetime import datetime
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorCollection

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

logger = logging.getLogger(__name__)


# ── Playlist Repository ─────────────────────────────────────────────────────────


class MongoPlaylistRepository(PlaylistRepository):
    """Motor-based persistence for Playlist aggregates."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    async def ensure_indexes(self) -> None:
        await self._col.create_index(
            [("title", "text"), ("description", "text"), ("tags", "text")]
        )
        await self._col.create_index([("city", 1), ("vibe", 1), ("budget_tier", 1)])
        await self._col.create_index([("like_count", -1), ("import_count", -1)])
        await self._col.create_index("creator_id")
        logger.info("Playlist indexes ensured")

    async def create(self, playlist: Playlist) -> Playlist:
        doc = _playlist_to_doc(playlist)
        doc["_id"] = str(uuid4())
        await self._col.insert_one(doc)
        playlist.id = doc["_id"]
        return playlist

    async def get_by_id(self, playlist_id: str) -> Playlist | None:
        doc = await self._col.find_one({"_id": playlist_id})
        return _doc_to_playlist(doc) if doc else None

    async def update(self, playlist: Playlist) -> Playlist | None:
        doc = _playlist_to_doc(playlist)
        doc.pop("_id", None)
        result = await self._col.find_one_and_update(
            {"_id": playlist.id},
            {"$set": doc},
            return_document=True,
        )
        return _doc_to_playlist(result) if result else None

    async def delete(self, playlist_id: str) -> bool:
        result = await self._col.delete_one({"_id": playlist_id})
        return result.deleted_count > 0

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
    ) -> list[Playlist]:
        query: dict = {"is_public": True}
        if city:
            query["city"] = {"$regex": city, "$options": "i"}
        if country:
            query["country"] = {"$regex": country, "$options": "i"}
        if vibe:
            query["vibe"] = {"$in": [v.strip() for v in vibe.split(",")]}
        if budget_tier:
            query["budget_tier"] = budget_tier
        if keyword:
            query["$text"] = {"$search": keyword}

        sort_map: dict = {
            "popular": [("like_count", -1), ("import_count", -1)],
            "newest": [("created_at", -1)],
            "top_rated": [("average_rating", -1), ("review_count", -1)],
        }
        sort_spec = sort_map.get(sort_by, sort_map["popular"])

        cursor = self._col.find(query).sort(sort_spec).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [_doc_to_playlist(d) for d in docs]

    async def get_by_creator(self, creator_id: str) -> list[Playlist]:
        cursor = self._col.find({"creator_id": creator_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        return [_doc_to_playlist(d) for d in docs]

    async def list_cities_with_playlists(self) -> list[str]:
        cities: list[str] = await self._col.distinct("city", {"is_public": True})
        return sorted(cities)

    async def increment_import_count(self, playlist_id: str) -> None:
        await self._col.update_one(
            {"_id": playlist_id}, {"$inc": {"import_count": 1}}
        )


# ── Review Repository ───────────────────────────────────────────────────────────


class MongoPlaylistReviewRepository(PlaylistReviewRepository):
    """Motor-based persistence for playlist reviews."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    async def ensure_indexes(self) -> None:
        await self._col.create_index("playlist_id")
        await self._col.create_index([("playlist_id", 1), ("user_id", 1)])
        logger.info("Playlist review indexes ensured")

    async def create(self, review: PlaylistReview) -> PlaylistReview:
        doc = {
            "_id": str(uuid4()),
            "playlist_id": review.playlist_id,
            "user_id": review.user_id,
            "user_first_name": review.user_first_name,
            "user_last_name": review.user_last_name,
            "rating": review.rating,
            "comment": review.comment,
            "created_at": review.created_at,
        }
        await self._col.insert_one(doc)
        review.id = doc["_id"]
        return review

    async def get_by_playlist(
        self, playlist_id: str, skip: int = 0, limit: int = 20
    ) -> list[PlaylistReview]:
        cursor = (
            self._col.find({"playlist_id": playlist_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [_doc_to_review(d) for d in docs]

    async def delete(self, review_id: str, user_id: str) -> bool:
        result = await self._col.delete_one({"_id": review_id, "user_id": user_id})
        return result.deleted_count > 0

    async def get_stats(self, playlist_id: str) -> tuple[float, int]:
        pipeline = [
            {"$match": {"playlist_id": playlist_id}},
            {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "cnt": {"$sum": 1}}},
        ]
        results = await self._col.aggregate(pipeline).to_list(length=1)
        if results:
            return float(results[0]["avg"]), int(results[0]["cnt"])
        return 0.0, 0


# ── Mapping helpers ──────────────────────────────────────────────────────────────


def _playlist_to_doc(p: Playlist) -> dict:
    return {
        "_id": p.id,
        "creator_id": p.creator_id,
        "city": p.city,
        "country": p.country,
        "title": p.title,
        "description": p.description,
        "cover_photo_url": p.cover_photo_url,
        "vibe": [v.value for v in p.vibe],
        "budget_tier": p.budget_tier.value,
        "items": [_item_to_doc(i) for i in p.items],
        "tags": p.tags,
        "total_days": p.total_days,
        "is_public": p.is_public,
        "like_count": p.like_count,
        "import_count": p.import_count,
        "liked_by": p.liked_by,
        "review_count": p.review_count,
        "average_rating": p.average_rating,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def _item_to_doc(i: PlaylistItem) -> dict:
    return {
        "item_type": i.item_type.value,
        "name": i.name,
        "day_number": i.day_number,
        "time_slot": i.time_slot.value,
        "order": i.order,
        "location_id": i.location_id,
        "category": i.category,
        "photo_url": i.photo_url,
        "latitude": i.latitude,
        "longitude": i.longitude,
        "address": i.address,
        "rating": i.rating,
        "num_reviews": i.num_reviews,
        "price_indicator": i.price_indicator,
        "note": i.note,
        "suggested_duration_minutes": i.suggested_duration_minutes,
    }


def _doc_to_playlist(doc: dict) -> Playlist:
    return Playlist(
        id=str(doc["_id"]),
        creator_id=doc["creator_id"],
        city=doc["city"],
        country=doc["country"],
        title=doc["title"],
        description=doc.get("description", ""),
        cover_photo_url=doc.get("cover_photo_url", ""),
        vibe=_parse_vibe_from_doc(doc.get("vibe", ["chill"])),
        budget_tier=BudgetTier(doc.get("budget_tier", "mid_range")),
        items=[_doc_to_item(i) for i in doc.get("items", [])],
        tags=doc.get("tags", []),
        total_days=doc.get("total_days", 1),
        is_public=doc.get("is_public", True),
        like_count=doc.get("like_count", 0),
        import_count=doc.get("import_count", 0),
        liked_by=doc.get("liked_by", []),
        review_count=doc.get("review_count", 0),
        average_rating=doc.get("average_rating", 0.0),
        created_at=doc.get("created_at", datetime.utcnow()),
        updated_at=doc.get("updated_at", datetime.utcnow()),
    )


def _doc_to_item(d: dict) -> PlaylistItem:
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


def _doc_to_review(d: dict) -> PlaylistReview:
    return PlaylistReview(
        id=str(d["_id"]),
        playlist_id=d["playlist_id"],
        user_id=d["user_id"],
        user_first_name=d.get("user_first_name", ""),
        user_last_name=d.get("user_last_name", ""),
        rating=d.get("rating", 5),
        comment=d.get("comment", ""),
        created_at=d.get("created_at", datetime.utcnow()),
    )


def _parse_vibe_from_doc(raw: str | list) -> list[PlaylistVibe]:
    """Handle both legacy single-string and new list format from MongoDB."""
    if isinstance(raw, list):
        return [PlaylistVibe(v) for v in raw]
    return [PlaylistVibe(raw)]

