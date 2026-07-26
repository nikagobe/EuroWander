from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.profiles.domain.entities import UserProfile
from app.modules.profiles.domain.interfaces import ProfileRepository


class MongoProfileRepository(ProfileRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    async def get_by_user_id(self, user_id: str) -> UserProfile | None:
        doc = await self._col.find_one({"user_id": user_id})
        return self._to_entity(doc) if doc else None

    async def upsert(self, profile: UserProfile) -> UserProfile:
        doc = {
            "user_id": profile.user_id,
            "bio": profile.bio,
            "home_city": profile.home_city,
            "base_airport": profile.base_airport,
            "profile_photo_url": profile.profile_photo_url,
            "cover_photo_url": profile.cover_photo_url,
            "preferred_languages": profile.preferred_languages,
            "travel_style_tags": profile.travel_style_tags,
            "updated_at": profile.updated_at,
        }
        result = await self._col.update_one(
            {"user_id": profile.user_id},
            {"$set": doc},
            upsert=True,
        )
        if not profile.id and result.upserted_id:
            profile.id = str(result.upserted_id)
        elif not profile.id:
            # Fetch the existing doc to get its _id
            existing = await self._col.find_one({"user_id": profile.user_id})
            if existing:
                profile.id = str(existing["_id"])
        return profile

    # ── Index ─────────────────────────────────────────────────────────────────

    async def ensure_indexes(self) -> None:
        await self._col.create_index("user_id", unique=True)

    # ── Mapping ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_entity(doc: dict) -> UserProfile:
        return UserProfile(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            bio=doc.get("bio", ""),
            home_city=doc.get("home_city", ""),
            base_airport=doc.get("base_airport", ""),
            profile_photo_url=doc.get("profile_photo_url", ""),
            cover_photo_url=doc.get("cover_photo_url", ""),
            preferred_languages=doc.get("preferred_languages", []),
            travel_style_tags=doc.get("travel_style_tags", []),
            updated_at=doc.get("updated_at", datetime.utcnow()),
        )


