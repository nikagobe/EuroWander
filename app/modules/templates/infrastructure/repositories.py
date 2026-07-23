"""MongoDB repository for TripTemplate."""

from dataclasses import asdict

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.templates.domain.entities import (
    FlightRecommendation,
    HotelPick,
    HotelRecommendations,
    TemplateLeg,
    TemplateStatus,
    TransportRecommendation,
    TripTemplate,
)
from app.modules.templates.domain.interfaces import TemplateRepository


class MongoTemplateRepository(TemplateRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def ensure_indexes(self) -> None:
        await self.collection.create_index("author_id")
        await self.collection.create_index("status")
        await self.collection.create_index("tags")
        await self.collection.create_index([("title", "text"), ("description", "text")])
        await self.collection.create_index("fork_count")
        await self.collection.create_index("created_at")

    async def create(self, template: TripTemplate) -> TripTemplate:
        doc = self._to_doc(template)
        doc.pop("_id", None)
        result = await self.collection.insert_one(doc)
        template.id = str(result.inserted_id)
        return template

    async def get_by_id(self, template_id: str) -> TripTemplate | None:
        try:
            doc = await self.collection.find_one({"_id": ObjectId(template_id)})
        except Exception:
            return None
        if doc is None:
            return None
        return self._from_doc(doc)

    async def update(self, template: TripTemplate) -> TripTemplate:
        doc = self._to_doc(template)
        doc.pop("_id", None)
        await self.collection.replace_one({"_id": ObjectId(template.id)}, doc)
        return template

    async def delete(self, template_id: str) -> bool:
        result = await self.collection.delete_one({"_id": ObjectId(template_id)})
        return result.deleted_count == 1

    async def list_published(
        self,
        skip: int = 0,
        limit: int = 20,
        tags: list[str] | None = None,
        destination: str | None = None,
        sort_by: str = "newest",
    ) -> list[TripTemplate]:
        query: dict = {"status": TemplateStatus.PUBLISHED.value}
        if tags:
            query["tags"] = {"$all": tags}
        if destination:
            query["legs.city"] = {"$regex": destination, "$options": "i"}

        sort_field = self._resolve_sort(sort_by)
        cursor = self.collection.find(query).sort(*sort_field).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [self._from_doc(d) for d in docs]

    async def list_by_author(self, author_id: str, skip: int = 0, limit: int = 20) -> list[TripTemplate]:
        cursor = (
            self.collection.find({"author_id": author_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [self._from_doc(d) for d in docs]

    async def increment_fork_count(self, template_id: str) -> None:
        await self.collection.update_one(
            {"_id": ObjectId(template_id)},
            {"$inc": {"fork_count": 1}},
        )

    # ─── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _resolve_sort(sort_by: str) -> tuple[str, int]:
        match sort_by:
            case "most_forked":
                return ("fork_count", -1)
            case "most_liked":
                return ("like_count", -1)
            case _:
                return ("created_at", -1)

    @staticmethod
    def _to_doc(template: TripTemplate) -> dict:
        doc: dict = {
            "author_id": template.author_id,
            "title": template.title,
            "description": template.description,
            "tags": template.tags,
            "cover_photo_url": template.cover_photo_url,
            "estimated_budget_min": template.estimated_budget_min,
            "estimated_budget_max": template.estimated_budget_max,
            "currency": template.currency,
            "total_days": template.total_days,
            "status": template.status.value,
            "fork_count": template.fork_count,
            "like_count": template.like_count,
            "liked_by": template.liked_by,
            "created_at": template.created_at,
            "updated_at": template.updated_at,
            "legs": [MongoTemplateRepository._leg_to_dict(leg) for leg in template.legs],
        }
        if template.id:
            doc["_id"] = ObjectId(template.id)
        return doc

    @staticmethod
    def _leg_to_dict(leg: TemplateLeg) -> dict:
        d: dict = {
            "order": leg.order,
            "city": leg.city,
            "country": leg.country,
            "days": leg.days,
            "playlist_id": leg.playlist_id,
            "restaurant_ids": leg.restaurant_ids,
            "author_notes": leg.author_notes,
        }
        if leg.flight_recommendation:
            d["flight_recommendation"] = asdict(leg.flight_recommendation)
        if leg.transport_recommendation:
            d["transport_recommendation"] = asdict(leg.transport_recommendation)
        if leg.hotel_recommendations:
            hr = leg.hotel_recommendations
            d["hotel_recommendations"] = {
                "city": hr.city,
                "country": hr.country,
                "primary_picks": [asdict(p) for p in hr.primary_picks],
                "fallback_neighborhood": hr.fallback_neighborhood,
                "fallback_star_min": hr.fallback_star_min,
                "fallback_star_max": hr.fallback_star_max,
                "fallback_budget_per_night_min": hr.fallback_budget_per_night_min,
                "fallback_budget_per_night_max": hr.fallback_budget_per_night_max,
            }
        return d

    @staticmethod
    def _from_doc(doc: dict) -> TripTemplate:
        legs: list[TemplateLeg] = []
        for leg_doc in doc.get("legs", []):
            fr = None
            if "flight_recommendation" in leg_doc:
                fr = FlightRecommendation(**leg_doc["flight_recommendation"])

            tr = None
            if "transport_recommendation" in leg_doc:
                tr = TransportRecommendation(**leg_doc["transport_recommendation"])

            hr = None
            if "hotel_recommendations" in leg_doc:
                hr_doc = leg_doc["hotel_recommendations"]
                picks = [HotelPick(**p) for p in hr_doc.get("primary_picks", [])]
                hr = HotelRecommendations(
                    city=hr_doc["city"],
                    country=hr_doc["country"],
                    primary_picks=picks,
                    fallback_neighborhood=hr_doc.get("fallback_neighborhood", ""),
                    fallback_star_min=hr_doc.get("fallback_star_min", 1),
                    fallback_star_max=hr_doc.get("fallback_star_max", 5),
                    fallback_budget_per_night_min=hr_doc.get("fallback_budget_per_night_min"),
                    fallback_budget_per_night_max=hr_doc.get("fallback_budget_per_night_max"),
                )

            legs.append(TemplateLeg(
                order=leg_doc["order"],
                city=leg_doc["city"],
                country=leg_doc["country"],
                days=leg_doc["days"],
                flight_recommendation=fr,
                transport_recommendation=tr,
                hotel_recommendations=hr,
                playlist_id=leg_doc.get("playlist_id", ""),
                restaurant_ids=leg_doc.get("restaurant_ids", []),
                author_notes=leg_doc.get("author_notes", ""),
            ))

        return TripTemplate(
            author_id=doc["author_id"],
            title=doc["title"],
            description=doc.get("description", ""),
            legs=legs,
            tags=doc.get("tags", []),
            cover_photo_url=doc.get("cover_photo_url", ""),
            estimated_budget_min=doc.get("estimated_budget_min"),
            estimated_budget_max=doc.get("estimated_budget_max"),
            currency=doc.get("currency", "EUR"),
            total_days=doc.get("total_days", 0),
            status=TemplateStatus(doc.get("status", "draft")),
            fork_count=doc.get("fork_count", 0),
            like_count=doc.get("like_count", 0),
            liked_by=doc.get("liked_by", []),
            id=str(doc["_id"]),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
        )

