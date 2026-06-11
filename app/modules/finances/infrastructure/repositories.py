from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.finances.domain.entities import Expense, ExpenseSource
from app.modules.finances.domain.interfaces import ExpenseRepository


class MongoExpenseRepository(ExpenseRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    async def create(self, expense: Expense) -> Expense:
        doc = self._to_doc(expense)
        result = await self._col.insert_one(doc)
        expense.id = str(result.inserted_id)
        return expense

    async def get_by_id(self, expense_id: str) -> Expense | None:
        try:
            oid = ObjectId(expense_id)
        except Exception:
            return None
        doc = await self._col.find_one({"_id": oid})
        return self._to_entity(doc) if doc else None

    async def list_by_trip(self, trip_id: str) -> list[Expense]:
        cursor = self._col.find({"trip_id": trip_id}).sort("created_at", 1)
        docs = await cursor.to_list(length=None)
        return [self._to_entity(d) for d in docs]

    async def delete(self, expense_id: str, trip_id: str) -> bool:
        try:
            oid = ObjectId(expense_id)
        except Exception:
            return False
        result = await self._col.delete_one({"_id": oid, "trip_id": trip_id})
        return result.deleted_count == 1

    async def update(
        self,
        expense_id: str,
        trip_id: str,
        name: str,
        amount: float,
        currency: str,
        paid_by: str,
        eligible_member_ids: list[str],
    ) -> bool:
        try:
            oid = ObjectId(expense_id)
        except Exception:
            return False
        result = await self._col.update_one(
            {"_id": oid, "trip_id": trip_id},
            {"$set": {
                "name": name,
                "amount": amount,
                "currency": currency,
                "paid_by": paid_by,
                "eligible_member_ids": eligible_member_ids,
            }},
        )
        return result.matched_count == 1

    async def get_by_source_ref(self, trip_id: str, source_ref: str) -> Expense | None:
        doc = await self._col.find_one({
            "trip_id": trip_id,
            "source": ExpenseSource.TICKET.value,
            "source_ref": source_ref,
        })
        return self._to_entity(doc) if doc else None

    async def ensure_indexes(self) -> None:
        await self._col.create_index("trip_id")
        await self._col.create_index([("trip_id", 1), ("source_ref", 1)])

    # ── Mapping ──────────────────────────────────────────────────────────────

    @staticmethod
    def _to_doc(e: Expense) -> dict:
        return {
            "trip_id": e.trip_id,
            "name": e.name,
            "amount": e.amount,
            "currency": e.currency,
            "paid_by": e.paid_by,
            "eligible_member_ids": e.eligible_member_ids,
            "source": e.source.value,
            "source_ref": e.source_ref,
            "created_at": e.created_at,
        }

    @staticmethod
    def _to_entity(doc: dict) -> Expense:
        return Expense(
            id=str(doc["_id"]),
            trip_id=doc["trip_id"],
            name=doc["name"],
            amount=doc["amount"],
            currency=doc.get("currency", "EUR"),
            paid_by=doc["paid_by"],
            eligible_member_ids=doc.get("eligible_member_ids", []),
            source=ExpenseSource(doc.get("source", "manual")),
            source_ref=doc.get("source_ref", ""),
            created_at=doc.get("created_at", datetime.utcnow()),
        )

