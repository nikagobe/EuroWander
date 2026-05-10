from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.users.domain.entities import User
from app.modules.users.domain.interfaces import UserRepository


class MongoUserRepository(UserRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    async def get_by_email(self, email: str) -> User | None:
        doc = await self._col.find_one({"email": email})
        return self._to_entity(doc) if doc else None

    async def get_by_id(self, user_id: str) -> User | None:
        try:
            oid = ObjectId(user_id)
        except Exception:
            return None
        doc = await self._col.find_one({"_id": oid})
        return self._to_entity(doc) if doc else None

    async def create(self, user: User) -> User:
        doc = {
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "password_hash": user.password_hash,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
        result = await self._col.insert_one(doc)
        user.id = str(result.inserted_id)
        return user

    # ── Index setup (called once at startup) ────────────────────────────────

    async def ensure_indexes(self) -> None:
        """Unique index on email so the DB enforces uniqueness even under race conditions."""
        await self._col.create_index("email", unique=True)

    # ── Mapping ─────────────────────────────────────────────────────────────

    @staticmethod
    def _to_entity(doc: dict) -> User:
        return User(
            id=str(doc["_id"]),
            email=doc["email"],
            first_name=doc["first_name"],
            last_name=doc["last_name"],
            password_hash=doc["password_hash"],
            is_active=doc.get("is_active", True),
            created_at=doc.get("created_at", datetime.utcnow()),
        )

