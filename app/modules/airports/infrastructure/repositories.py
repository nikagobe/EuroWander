import re

from motor.motor_asyncio import AsyncIOMotorCollection

from app.modules.airports.domain.entities import Airport
from app.modules.airports.domain.interfaces import AirportRepository


class MongoAirportRepository(AirportRepository):

    def __init__(self, collection: AsyncIOMotorCollection) -> None:
        self._col = collection

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _to_entity(doc: dict) -> Airport:
        return Airport(
            wikidata_id=doc.get("wikidata_id", ""),
            name=doc.get("name", ""),
            iata_code=doc.get("iata_code", ""),
            country_code=doc.get("country_code", ""),
            lat=doc.get("lat"),
            lng=doc.get("lng"),
        )

    # ── interface implementation ───────────────────────────────────────────────

    async def get_by_iata(self, iata_code: str) -> Airport | None:
        doc = await self._col.find_one({"iata_code": iata_code.upper()})
        return self._to_entity(doc) if doc else None

    async def get_by_country(self, country_code: str) -> list[Airport]:
        cursor = self._col.find(
            {"country_code": country_code.upper()},
            sort=[("name", 1)],
        )
        docs = await cursor.to_list(length=None)
        return [self._to_entity(d) for d in docs]

    async def search(self, query: str, limit: int = 10) -> list[Airport]:
        """
        Search by IATA code (exact, case-insensitive) or airport name prefix.
        IATA match is tried first; falls back to name prefix regex.
        """
        # Exact IATA match
        if re.fullmatch(r"[A-Za-z]{3}", query):
            doc = await self._col.find_one({"iata_code": query.upper()})
            if doc:
                return [self._to_entity(doc)]

        # Name prefix search
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        cursor = self._col.find(
            {"name": {"$regex": pattern}},
            sort=[("name", 1)],
            limit=limit,
        )
        docs = await cursor.to_list(length=limit)
        return [self._to_entity(d) for d in docs]

