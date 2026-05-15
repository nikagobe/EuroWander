from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.cities.domain.entities import City
from app.modules.cities.domain.interfaces import CityRepository


class MongoCityRepository(CityRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def search_by_name(self, query: str, limit: int) -> list[City]:
        # Case-insensitive prefix match, sorted by wikidata_num (lower = bigger city)
        cursor = self.collection.find(
            {"name": {"$regex": f"^{query}", "$options": "i"}}
        ).sort("wikidata_num", 1).limit(limit)

        docs = await cursor.to_list(length=limit)
        return [self._to_entity(doc) for doc in docs]

    @staticmethod
    def _to_entity(doc: dict) -> City:
        return City(
            wikidata_id=doc.get("wikidata_id", ""),
            name=doc.get("name", ""),
            description=doc.get("description", ""),
            country=doc.get("country", "").capitalize(),
            freebase_id=doc.get("freebase_id", ""),
            lat=doc.get("lat"),
            lng=doc.get("lng"),
        )

