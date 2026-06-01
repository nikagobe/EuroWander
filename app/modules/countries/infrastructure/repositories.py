from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.countries.domain.entities import Country, MajorCity
from app.modules.countries.domain.interfaces import CountryRepository


class MongoCountryRepository(CountryRepository):
    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self.collection = collection

    async def get_by_name(self, name: str) -> Country | None:
        doc = await self.collection.find_one({"name": name})
        if doc is None:
            return None
        return self._to_entity(doc)

    async def get_neighbors_with_cities(self, name: str) -> list[Country]:
        """Fetch the source country, then retrieve all neighbor documents."""
        source = await self.collection.find_one({"name": name})
        if source is None:
            return []

        neighbor_names: list[str] = source.get("neighbors", [])
        if not neighbor_names:
            return []

        cursor = self.collection.find({"name": {"$in": neighbor_names}})
        docs = await cursor.to_list(length=None)
        return [self._to_entity(doc) for doc in docs]

    async def get_city_by_iata(self, iata_code: str) -> MajorCity | None:
        """Find the major city that has this IATA code in its airports list."""
        iata_upper = iata_code.upper()
        doc = await self.collection.find_one(
            {"major_cities.airports": iata_upper},
            {"major_cities.$": 1},
        )
        if not doc:
            return None
        cities = doc.get("major_cities", [])
        if not cities:
            return None
        c = cities[0]
        return MajorCity(
            name=c.get("name", ""),
            wikidata_id=c.get("wikidata_id", ""),
            freebase_id=c.get("freebase_id", ""),
            description=c.get("description", ""),
        )

    @staticmethod
    def _to_entity(doc: dict) -> Country:
        major_cities = [
            MajorCity(
                name=c.get("name", ""),
                wikidata_id=c.get("wikidata_id", ""),
                freebase_id=c.get("freebase_id", ""),
                description=c.get("description", ""),
            )
            for c in doc.get("major_cities", [])
        ]
        return Country(
            name=doc.get("name", ""),
            neighbors=doc.get("neighbors", []),
            major_cities=major_cities,
        )

