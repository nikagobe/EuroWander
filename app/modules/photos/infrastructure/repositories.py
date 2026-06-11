"""
MongoDB repository for photo metadata.
"""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.photos.domain.entities import Photo
from app.modules.photos.domain.interfaces import PhotoRepository


class MongoPhotoRepository(PhotoRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    # ── Write ──────────────────────────────────────────────────────────────────

    async def create(self, photo: Photo) -> Photo:
        raw = {
            "trip_id": photo.trip_id,
            "uploaded_by": photo.uploaded_by,
            "file_name": photo.file_name,
            "file_key": photo.file_key,
            "content_type": photo.content_type,
            "size_bytes": photo.size_bytes,
            "caption": photo.caption,
            "created_at": photo.created_at,
        }
        result = await self._col.insert_one(raw)
        photo.id = str(result.inserted_id)
        return photo

    async def delete(self, photo_id: str) -> bool:
        try:
            oid = ObjectId(photo_id)
        except Exception:
            return False
        result = await self._col.delete_one({"_id": oid})
        return result.deleted_count == 1

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_by_id(self, photo_id: str) -> Photo | None:
        try:
            oid = ObjectId(photo_id)
        except Exception:
            return None
        raw = await self._col.find_one({"_id": oid})
        if raw is None:
            return None
        return self._to_entity(raw)

    async def list_by_trip(self, trip_id: str) -> list[Photo]:
        cursor = self._col.find({"trip_id": trip_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        return [self._to_entity(d) for d in docs]

    async def list_by_trip_paginated(
        self, trip_id: str, skip: int, limit: int
    ) -> list[Photo]:
        cursor = (
            self._col.find({"trip_id": trip_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [self._to_entity(d) for d in docs]

    async def count_by_trip(self, trip_id: str) -> int:
        return await self._col.count_documents({"trip_id": trip_id})

    # ── Indexes ────────────────────────────────────────────────────────────────

    async def ensure_indexes(self) -> None:
        await self._col.create_index("trip_id")

    # ── Mapping ────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_entity(raw: dict) -> Photo:
        return Photo(
            id=str(raw["_id"]),
            trip_id=raw["trip_id"],
            uploaded_by=raw["uploaded_by"],
            file_name=raw["file_name"],
            file_key=raw["file_key"],
            content_type=raw["content_type"],
            size_bytes=raw["size_bytes"],
            caption=raw.get("caption", ""),
            created_at=raw["created_at"],
        )

