"""
MongoDB repository for document metadata.
"""

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.documents.domain.entities import Document, DocumentCategory
from app.modules.documents.domain.interfaces import DocumentRepository


class MongoDocumentRepository(DocumentRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    # ── Write ──────────────────────────────────────────────────────────────────

    async def create(self, doc: Document) -> Document:
        raw = {
            "trip_id": doc.trip_id,
            "uploaded_by": doc.uploaded_by,
            "file_name": doc.file_name,
            "file_key": doc.file_key,
            "content_type": doc.content_type,
            "size_bytes": doc.size_bytes,
            "category": doc.category.value,
            "created_at": doc.created_at,
        }
        result = await self._col.insert_one(raw)
        doc.id = str(result.inserted_id)
        return doc

    async def delete(self, doc_id: str) -> bool:
        try:
            oid = ObjectId(doc_id)
        except Exception:
            return False
        result = await self._col.delete_one({"_id": oid})
        return result.deleted_count == 1

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_by_id(self, doc_id: str) -> Document | None:
        try:
            oid = ObjectId(doc_id)
        except Exception:
            return None
        raw = await self._col.find_one({"_id": oid})
        if raw is None:
            return None
        return self._to_entity(raw)

    async def list_by_trip(self, trip_id: str) -> list[Document]:
        cursor = self._col.find({"trip_id": trip_id}).sort("created_at", -1)
        docs = await cursor.to_list(length=None)
        return [self._to_entity(d) for d in docs]

    async def count_by_trip(self, trip_id: str) -> int:
        return await self._col.count_documents({"trip_id": trip_id})

    # ── Indexes ────────────────────────────────────────────────────────────────

    async def ensure_indexes(self) -> None:
        await self._col.create_index("trip_id")

    # ── Mapping ────────────────────────────────────────────────────────────────

    @staticmethod
    def _to_entity(raw: dict) -> Document:
        return Document(
            id=str(raw["_id"]),
            trip_id=raw["trip_id"],
            uploaded_by=raw["uploaded_by"],
            file_name=raw["file_name"],
            file_key=raw["file_key"],
            content_type=raw["content_type"],
            size_bytes=raw["size_bytes"],
            category=DocumentCategory(raw["category"]),
            created_at=raw["created_at"],
        )

