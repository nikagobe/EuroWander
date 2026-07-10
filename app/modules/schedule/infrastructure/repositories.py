"""MongoDB repository for manual schedule items."""

import logging
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.schedule.domain.entities import ScheduleItem, ScheduleItemType, TimeSlot
from app.modules.schedule.domain.interfaces import ScheduleRepository

logger = logging.getLogger(__name__)


class MongoScheduleRepository(ScheduleRepository):
    """Persists manual schedule items (attractions, restaurants) in MongoDB."""

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._collection = collection

    async def ensure_indexes(self) -> None:
        """Create indexes for fast trip-based lookups."""
        await self._collection.create_index("trip_id")
        await self._collection.create_index([("trip_id", 1), ("day_date", 1)])
        logger.info("Schedule indexes ensured")

    async def get_manual_items(self, trip_id: str) -> list[ScheduleItem]:
        """Get all manual schedule items for a trip."""
        cursor = self._collection.find({"trip_id": trip_id})
        docs = await cursor.to_list(length=None)
        return [_doc_to_entity(doc) for doc in docs]

    async def add_item(self, trip_id: str, item: ScheduleItem) -> ScheduleItem:
        """Persist a new manual schedule item."""
        item_id = str(uuid4())
        doc = {
            "_id": item_id,
            "trip_id": trip_id,
            "day_date": item.day_date,
            "time_slot": item.time_slot.value,
            "item_type": item.item_type.value,
            "title": item.title,
            "subtitle": item.subtitle,
            "reference_id": item.reference_id,
            "note": item.note,
            "is_auto": False,
            "order": item.order,
        }
        await self._collection.insert_one(doc)
        item.id = item_id
        return item

    async def update_item(
        self,
        trip_id: str,
        item_id: str,
        day_date: str | None = None,
        time_slot: str | None = None,
        title: str | None = None,
        subtitle: str | None = None,
        note: str | None = None,
        order: int | None = None,
    ) -> ScheduleItem | None:
        """Update a manual schedule item. Returns None if not found."""
        update_fields: dict = {}
        if day_date is not None:
            update_fields["day_date"] = day_date
        if time_slot is not None:
            update_fields["time_slot"] = time_slot
        if title is not None:
            update_fields["title"] = title
        if subtitle is not None:
            update_fields["subtitle"] = subtitle
        if note is not None:
            update_fields["note"] = note
        if order is not None:
            update_fields["order"] = order

        if not update_fields:
            # Nothing to update — just fetch and return
            doc = await self._collection.find_one({"_id": item_id, "trip_id": trip_id, "is_auto": False})
            return _doc_to_entity(doc) if doc else None

        result = await self._collection.find_one_and_update(
            {"_id": item_id, "trip_id": trip_id, "is_auto": False},
            {"$set": update_fields},
            return_document=True,
        )
        return _doc_to_entity(result) if result else None

    async def remove_item(self, trip_id: str, item_id: str) -> bool:
        """Remove a manual schedule item. Returns False if not found."""
        result = await self._collection.delete_one(
            {"_id": item_id, "trip_id": trip_id, "is_auto": False}
        )
        return result.deleted_count > 0


def _doc_to_entity(doc: dict) -> ScheduleItem:
    """Map a MongoDB document to a ScheduleItem domain entity."""
    return ScheduleItem(
        id=str(doc["_id"]),
        day_date=doc["day_date"],
        time_slot=TimeSlot(doc["time_slot"]),
        item_type=ScheduleItemType(doc["item_type"]),
        title=doc["title"],
        subtitle=doc.get("subtitle", ""),
        reference_id=doc.get("reference_id", ""),
        note=doc.get("note", ""),
        is_auto=doc.get("is_auto", False),
        order=doc.get("order", 0),
    )

